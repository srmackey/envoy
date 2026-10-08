"""Read-only snapshot for the local page.

One call returns the whole tree with a health verdict per chair, the board of
the nexus in view, what needs attention under it, and a briefing for the chair
that is open. Cards about the open chair travel with its briefing, and the
nexus keeps the rest. The page displays it and decides nothing.

It reads the board, the roster, published sitreps, the local status file, and
pending inbox files. It never lists mail notes, so a refresh does not mark a
note seen.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from envoy.address import Nexus, Tree, load_tree, resolve
from envoy.mapfile import Chair, map_list, open_chair
from envoy.notes_store import mail_outstanding
from envoy.now import now_view
from envoy.status_store import status_get

STALE_DAYS = 7
SOON_DAYS = 7

_SKIP_INBOX = {"_log.md", "README.md"}
_FIELDS = (
    "forefront",
    "where_i_left_off",
    "next_steps",
    "open_loops",
    "repo",
)
_ISO = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MARKUP = re.compile(r"\*\*|__|`")
_ORDER = ("overdue", "due", "mail", "inbox", "unaccounted", "drift", "always_on")
_LIST_MARK = re.compile(r"^(?:[-*]|\d+[.)])\s+")


def snapshot(
    root: Path,
    home: Path,
    chair: str | None = None,
    *,
    since: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    tree = load_tree(root)
    top = _top_address(tree)
    selected = open_chair(root, chair or top, home)
    if selected is None:
        return {"ok": False, "error": "unknown_chair"}
    view = selected.address if selected.is_nexus else _nexus_of(selected)
    chairs = _tree(root, home, tree, top, today)
    index = {entry["address"]: entry for entry in _walk(chairs)}
    board = _board(root, home, tree, view, today)
    attention = _attention(board, index.get(view))
    briefing = node_detail(root, home, view, selected.address)
    if briefing.get("ok"):
        briefing["health"] = (index.get(selected.address) or {}).get("health")
        briefing["kind"] = "nexus" if selected.is_nexus else "node"
        # The chair's own cards ride with its briefing; the nexus keeps the rest.
        briefing["attention"] = [card for card in attention if card.get("address") == selected.address]
        attention = [card for card in attention if card.get("address") != selected.address]
    nexus = {key: value for key, value in (index.get(view) or {}).items() if key != "children"}
    payload: dict[str, Any] = {
        "ok": True,
        "today": today.isoformat(),
        "chair": selected.address,
        "view": view,
        "path": _path(index, chairs, selected.address),
        "tree": chairs,
        "nexus": nexus or None,
        "board": board,
        "next": _next(board),
        "attention": attention,
        "briefing": briefing,
        "mail_unacked": sum(entry["health"]["mail"] for entry in index.values()),
        "inbox_count": sum(entry["health"]["inbox"] for entry in index.values()),
    }
    version = hashlib.sha1(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:12]
    if since and since == version:
        return {"ok": True, "unchanged": True, "version": version}
    payload["version"] = version
    return payload


def node_detail(root: Path, home: Path, chair: str, node: str) -> dict[str, Any]:
    if not chair or not node:
        return {"ok": False, "error": "invalid_payload"}
    caller = open_chair(root, chair, home)
    target = open_chair(root, node, home)
    if caller is None or target is None:
        return {"ok": False, "error": "unknown_chair"}
    got = status_get(root, home, chair, node)
    if got.get("error") == "forbidden":
        return got
    published = got.get("document") if got.get("ok") else None
    local = read_local_status(target)
    sensitive = _sensitive(root, target.address)
    # A sensitive chair publishes a thinner sitrep on purpose, so the two copies
    # are expected to differ.
    differs = [] if sensitive else _differs(published, local)
    return {
        "ok": True,
        "address": target.address,
        "sensitive": sensitive,
        "published": published,
        "local": local,
        "diverged": bool(differs),
        "differs": differs,
        "inbox_count": count_inbox(target),
    }


def count_inbox(chair: Chair) -> int:
    inbox = local_dir(chair) / "inbox"
    if not inbox.is_dir():
        return 0
    count = 0
    for path in inbox.iterdir():
        if not path.is_file():
            continue
        if path.name in _SKIP_INBOX:
            continue
        count += 1
    return count


def read_local_status(chair: Chair) -> dict[str, Any] | None:
    path = local_dir(chair) / "_status" / "STATUS.md"
    if not path.is_file():
        return None
    return _parse_status(path.read_text(encoding="utf-8"))


def local_dir(chair: Chair) -> Path:
    if not chair.legacy:
        overlay = chair.home.parent / "_contextforge" / "workspaces" / chair.slug
        if overlay.is_dir():
            return overlay
    return chair.project_dir


# The tree -----------------------------------------------------------------


def _top_address(tree: Tree | None) -> str:
    return "nexus" if tree is None else tree.top.name.casefold()


def _nexus_of(chair: Chair) -> str:
    if chair.legacy or "/" not in chair.address:
        return "nexus" if chair.legacy else chair.address
    return chair.address.split("/", 1)[0]


def _tree(
    root: Path,
    home: Path,
    tree: Tree | None,
    top: str,
    today: date,
) -> list[dict[str, Any]]:
    if tree is None:
        entry = _entry(root, home, top, top, "nexus", "nexus", False, "active", False, today)
        names = [str(item.get("name") or "") for item in map_list(root, top).get("entries") or []]
        entry["children"] = [
            _entry(root, home, top, name, name, "node", False, "active", False, today)
            for name in names
            if name and name != top
        ]
        return [entry]

    def build(nexus: Nexus, status: str, always_on: bool) -> dict[str, Any]:
        address = nexus.name.casefold()
        entry = _entry(
            root, home, top, address, nexus.name, "nexus",
            nexus.sensitive, status, always_on, today,
        )
        children: list[dict[str, Any]] = []
        for row in nexus.nodes:
            if row.kind == "nexus":
                child = _child_nexus(tree, nexus, row.path)
                if child is not None:
                    children.append(build(child, row.status, row.always_on))
                continue
            children.append(
                _entry(
                    root, home, top, f"{address}/{row.name.casefold()}", row.name, "node",
                    row.sensitive or nexus.sensitive, row.status, row.always_on, today,
                )
            )
        entry["children"] = children
        return entry

    return [build(tree.top, "active", False)]


def _child_nexus(tree: Tree, parent: Nexus, rel: str) -> Nexus | None:
    want = (parent.folder / rel.strip().strip("/")).resolve()
    for nexus in tree.nexuses.values():
        if nexus.parent and nexus.parent.casefold() == parent.name.casefold():
            if nexus.folder.resolve() == want:
                return nexus
    return None


def _entry(
    root: Path,
    home: Path,
    top: str,
    address: str,
    name: str,
    kind: str,
    sensitive: bool,
    status: str,
    always_on: bool,
    today: date,
) -> dict[str, Any]:
    target = open_chair(root, address, home)
    published = None
    local = None
    inbox = 0
    mail = 0
    if target is not None:
        got = status_get(root, home, top, target.address)
        published = got.get("document") if got.get("ok") else None
        local = read_local_status(target)
        inbox = count_inbox(target)
        mail = len(mail_outstanding(target.home, target.address)["mail_unacked_for_me"])
    doc = published or local or {}
    return {
        "address": target.address if target is not None else address,
        "name": name,
        "kind": kind,
        "sensitive": sensitive,
        "status": status,
        "always_on": always_on,
        "forefront": str(doc.get("forefront") or ""),
        "health": _health(published, local, inbox, mail, today, sensitive=sensitive),
    }


def _health(
    published: dict[str, Any] | None,
    local: dict[str, Any] | None,
    inbox: int,
    mail: int,
    today: date,
    *,
    sensitive: bool = False,
) -> dict[str, Any]:
    doc = published or local
    updated = _local_day(str((doc or {}).get("updated") or ""))
    age = (today - updated).days if updated else None
    forefront = str((doc or {}).get("forefront") or "")
    past = any(day < today for day in map(_day, _ISO.findall(forefront)) if day)
    stale_reason = None
    if age is not None and age > STALE_DAYS:
        stale_reason = "old"
    elif past:
        stale_reason = "past_date"
    drift = not sensitive and bool(_differs(published, local))
    repo = str((doc or {}).get("repo") or "")
    if doc is None:
        state = "silent"
    elif drift:
        state = "drift"
    elif stale_reason:
        state = "stale"
    else:
        state = "fresh"
    return {
        "state": state,
        "published": published is not None,
        "local": local is not None,
        "updated": updated.isoformat() if updated else "",
        "age_days": age,
        "stale": stale_reason is not None,
        "stale_reason": stale_reason,
        "drift": drift,
        "repo": repo,
        "dirty": "dirty" in repo.casefold(),
        "inbox": inbox,
        "mail": mail,
    }


def _walk(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for entry in entries:
        found.append(entry)
        found.extend(_walk(entry.get("children") or []))
    return found


def _path(index: dict[str, dict], tree: list[dict[str, Any]], address: str) -> list[dict[str, str]]:
    def search(entries: list[dict[str, Any]], trail: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
        for entry in entries:
            here = trail + [entry]
            if entry["address"] == address:
                return here
            hit = search(entry.get("children") or [], here)
            if hit:
                return hit
        return None

    found = search(tree, []) or ([index[address]] if address in index else [])
    return [{"address": entry["address"], "name": entry["name"]} for entry in found]


# The board ----------------------------------------------------------------


def _board(root: Path, home: Path, tree: Tree | None, view: str, today: date) -> dict[str, Any]:
    snap = now_view(root, home, view, read_only=True)
    if snap.get("error") == "missing_now":
        return {"nexus": view, "missing": True, "sections": [], "always_on_missing": []}
    if not snap.get("ok"):
        return {"nexus": view, "missing": True, "sections": [], "always_on_missing": [], "error": snap.get("error")}
    states = {(row["text"], row["node"]): row["state"] for row in snap.get("reconcile") or []}
    sections: list[dict[str, Any]] = []
    focus = snap.get("focus")
    if focus:
        name = str(focus.get("node") or "")
        sensitive = _sensitive_name(tree, name)
        sections.append(_section(tree, name, sensitive, focus, states, today))
    view_sensitive = _sensitive_name(tree, view)
    sections.append(_section(tree, view, view_sensitive, snap.get("now") or {}, states, today))
    return {
        "nexus": view,
        "missing": False,
        "sections": sections,
        "always_on_missing": list(snap.get("always_on_missing") or []),
    }


def _section(
    tree: Tree | None,
    name: str,
    sensitive: bool,
    parsed: dict[str, Any],
    states: dict[tuple[str, str], str],
    today: date,
) -> dict[str, Any]:
    def items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in rows or []:
            node = row.get("node")
            located = resolve(tree, node, root_alias=True) if tree is not None and node else None
            due = _day(str(row.get("due") or ""))
            out.append({
                "text": row["text"],
                "node": node,
                "address": located.address if located else None,
                "due": row.get("due"),
                "days": (due - today).days if due else None,
                "state": states.get((row["text"], node)) if node else None,
                "sensitive": sensitive or bool(located and located.sensitive),
            })
        return out

    return {
        "name": name,
        "sensitive": sensitive,
        "updated": parsed.get("updated") or "",
        "this_week": items(parsed.get("this_week") or []),
        "later": items(parsed.get("later") or []),
    }


def _next(board: dict[str, Any]) -> dict[str, Any] | None:
    for section in board.get("sections") or []:
        if section["this_week"]:
            return {**section["this_week"][0], "board": section["name"]}
    return None


def _attention(board: dict[str, Any], view: dict[str, Any] | None) -> list[dict[str, Any]]:
    """One card per thing that needs the principal, carrying every reason it does.

    A board line is one thing; a chair is another. `kinds` is ordered by urgency,
    and `kind` is the first of them.
    """
    cards: dict[tuple, dict[str, Any]] = {}

    def add(key: tuple, kind: str, fields: dict[str, Any]) -> None:
        card = cards.setdefault(key, {"kinds": [], **fields})
        card.update(fields)
        card["kinds"].append(kind)

    for section in board.get("sections") or []:
        for when in ("this_week", "later"):
            for row in section[when]:
                key = ("line", row["text"], row["node"])
                days = row["days"]
                if days is not None and days < 0:
                    add(key, "overdue", row)
                elif days is not None and days <= SOON_DAYS:
                    add(key, "due", row)
                if row["state"] == "unaccounted":
                    add(key, "unaccounted", row)
    for name in board.get("always_on_missing") or []:
        add(("always_on", name), "always_on", {"node": name, "address": None, "sensitive": False})
    for entry in _walk([view] if view else []):
        health = entry["health"]
        key = ("chair", entry["address"])
        base = {"address": entry["address"], "node": entry["name"], "sensitive": entry["sensitive"]}
        if health["mail"]:
            add(key, "mail", {**base, "mail": health["mail"]})
        if health["inbox"]:
            add(key, "inbox", {**base, "inbox": health["inbox"]})
        if health["drift"]:
            add(key, "drift", base)
    items = list(cards.values())
    for card in items:
        card["kinds"].sort(key=_ORDER.index)
        card["kind"] = card["kinds"][0]
    items.sort(key=lambda card: (_ORDER.index(card["kind"]), card.get("days") or 0))
    return items


# Status files -------------------------------------------------------------


def _sensitive(root: Path, address: str) -> bool:
    tree = load_tree(root)
    if tree is None:
        return False
    located = resolve(tree, address, root_alias=True)
    return bool(located and located.sensitive)


def _sensitive_name(tree: Tree | None, name: str) -> bool:
    if tree is None or not name:
        return False
    located = resolve(tree, name, root_alias=True)
    return bool(located and located.sensitive)


def _day(text: str) -> date | None:
    match = _ISO.search(text)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _local_day(text: str) -> date | None:
    """The calendar day here. A published sitrep stamps UTC; a local file writes a bare date."""
    try:
        stamp = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return _day(text)
    if stamp.tzinfo is None:
        return stamp.date()
    return stamp.astimezone().date()


def _parse_status(text: str) -> dict[str, Any]:
    updated = ""
    repo = ""
    sections = {
        "forefront": [],
        "where i left off": [],
        "next steps": [],
        "open loops": [],
    }
    current: list[str] | None = None
    started = False
    for line in text.splitlines():
        stripped = line.strip()
        lowered = stripped.lower()
        if stripped.startswith("## "):
            started = True
            title = stripped[3:].strip().lower()
            current = sections.get(title)
            continue
        if not started:
            if lowered.startswith("updated:"):
                updated = stripped.split(":", 1)[1].strip()
            elif lowered.startswith("repo:"):
                repo = stripped.split(":", 1)[1].strip()
            continue
        if current is None or not stripped:
            continue
        current.append(_LIST_MARK.sub("", stripped).strip())
    forefront = sections["forefront"]
    return {
        "updated": updated,
        "repo": repo,
        "forefront": forefront[0] if forefront else "",
        "where_i_left_off": sections["where i left off"],
        "next_steps": sections["next steps"],
        "open_loops": sections["open loops"],
    }


def _plain(text: str) -> str:
    """Text as a reader sees it: inline markup and links reduced to their words."""
    return " ".join(_MARKUP.sub("", _LINK.sub(r"\1", text)).split())


def _norm_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = _plain(value)
        return [text] if text else []
    if not isinstance(value, list):
        return []
    return [_plain(str(item)) for item in value if str(item).strip()]


def _differs(published: dict[str, Any] | None, local: dict[str, Any] | None) -> list[str]:
    if not published or not local:
        return []
    return [
        field
        for field in _FIELDS
        if _norm_list(published.get(field)) != _norm_list(local.get(field))
    ]
