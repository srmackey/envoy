"""Read-only snapshot for the local page.

One call returns the whole tree with a health verdict per chair, the board of
the nexus in view, what under it needs the principal, what an agent can clear
on its own, and a briefing for the chair that is open. Cards about the open
chair travel with its briefing, and the nexus keeps the rest. Every signal
carries who clears it and how. The page displays it and decides nothing.

It reads the board, the roster, published sitreps, the local status file,
pending inbox files, desk files, and settle-pass leftovers. It never lists mail
notes, so a refresh does not mark a note seen.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from envoy.address import Nexus, Tree, load_tree, resolve
from envoy.mapfile import Chair, map_list, open_chair
from envoy.notes_store import mail_outstanding
from envoy.now import now_view
from envoy.status_store import status_get

_SKIP_INBOX = {"_log.md", "README.md"}
_SKIP_DESK = {"README.md", "desktop.ini", "Thumbs.db"}
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
_LIST_MARK = re.compile(r"^(?:[-*]|\d+[.)])\s+")
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
_BULLET = re.compile(r"^[-*]\s+([A-Za-z_ ]+):\s*(.*)$")
_WAIT_FIELDS = ("surface", "line", "why")

# Who clears each signal, in order of urgency. A notice is the principal's too, but
# it is plain state: it is listed with its fix and never colors a chair.
_CLASS = {
    "date_passed": "needs_you",
    "waiting": "needs_you",
    "unaccounted": "needs_you",
    "always_on": "needs_you",
    "inbox": "notice",
    "drift": "housekeeping",
    "mail": "housekeeping",
    "no_sitrep": "housekeeping",
}
_ORDER = tuple(_CLASS)
_RANK = {"housekeeping": 1, "needs_you": 2}

# How each signal clears. With nexus.md present the step names the command and
# the folder to run it in. On its own, Envoy says the same job in plain words.
_SETTLE_ALL = " /settle-pass all from {top} clears every chair at once."
_NAMED = {
    "date_passed": ("weekly review", "board", "Run weekly review in {board}: finish, re-date, or drop the line."),
    "waiting": (None, "held", "Open a session in {held}. The settle-wait report comes up at the start: resolve it there, or change the line in {chair}."),
    "inbox": ("process the inbox", "chair", "Say process the inbox in {chair}."),
    "unaccounted": ("weekly review", "board", "Run weekly review in {board} to change the line, or work in {chair} until its Forefront carries it."),
    "always_on": ("weekly review", "board", "Run weekly review in {board} and give {chair} a line this week."),
    "drift": ("/settle", "chair", "Run /settle in {chair} to republish its sitrep from the status file." + _SETTLE_ALL),
    "mail": ("/settle", "chair", "Run /settle in {chair} so the chair sees its mail." + _SETTLE_ALL),
    "no_sitrep": ("/settle", "chair", "Run /settle in {chair} to write its status file and publish it." + _SETTLE_ALL),
}
_PLAIN = {
    "date_passed": "Finish, re-date, or drop the board line.",
    "waiting": "Resolve the item, or change the line it names.",
    "inbox": "Process the letters in this chair's inbox.",
    "unaccounted": "Change the board line, or work the chair until its Forefront carries it.",
    "always_on": "Give this chair a line on this week's board.",
    "drift": "Republish this chair's sitrep from its status file.",
    "mail": "Have this chair list its mail so the note is marked seen.",
    "no_sitrep": "Write this chair's status file and publish it.",
}


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
    waiting = _settle_wait(root, home, tree)
    chairs = _tree(root, home, tree, top, today, waiting)
    index = {entry["address"]: entry for entry in _walk(chairs)}
    titles = {address: entry["title"] for address, entry in index.items()}
    boards = {
        address: _board(root, home, tree, address, today, titles)
        for address, entry in index.items()
        if entry["kind"] == "nexus"
    }
    board = boards.get(view) or _board(root, home, tree, view, today, titles)
    guide = _Guide(root, home, tree, top)
    cards = _cards(index, boards, waiting, guide)
    _rank_chairs(index, cards)
    under = {entry["address"] for entry in _walk([index[view]])} if view in index else set()
    here = [card for card in cards if _within(card, under)]
    needs = [card for card in here if card["class"] in ("needs_you", "notice")]
    chores = [card for card in here if card["class"] == "housekeeping"]
    briefing = node_detail(root, home, view, selected.address)
    if briefing.get("ok"):
        briefing["title"] = titles.get(selected.address) or selected.address
        briefing["health"] = (index.get(selected.address) or {}).get("health")
        briefing["kind"] = "nexus" if selected.is_nexus else "node"
        # The chair's own cards ride with its briefing; the nexus keeps the rest.
        briefing["attention"] = [card for card in needs if card.get("address") == selected.address]
        briefing["housekeeping"] = [card for card in chores if card.get("address") == selected.address]
        needs = [card for card in needs if card.get("address") != selected.address]
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
        "attention": needs,
        "housekeeping": _housekeeping(chores, guide, view),
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


def count_desk(chair: Chair) -> int:
    """Files on the principal's desk. The desk is on the checkout, not the overlay."""
    desk = chair.project_dir / "desk"
    if not desk.is_dir():
        return 0
    return sum(
        1
        for path in desk.iterdir()
        if path.is_file() and path.name not in _SKIP_DESK and not path.name.startswith(".")
    )


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
    waiting: dict[str, dict[str, Any]],
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

    def build(nexus: Nexus, status: str, always_on: bool, services: tuple[str, ...] | None) -> dict[str, Any]:
        address = nexus.name.casefold()
        entry = _entry(
            root, home, top, address, nexus.name, "nexus",
            nexus.sensitive, status, always_on, today,
            services=services, waiting=waiting,
        )
        children: list[dict[str, Any]] = []
        for row in nexus.nodes:
            if row.kind == "nexus":
                child = _child_nexus(tree, nexus, row.path)
                if child is not None:
                    children.append(build(child, row.status, row.always_on, row.services))
                continue
            children.append(
                _entry(
                    root, home, top, f"{address}/{row.name.casefold()}", row.name, "node",
                    row.sensitive or nexus.sensitive, row.status, row.always_on, today,
                    services=row.services, waiting=waiting,
                )
            )
        entry["children"] = children
        return entry

    return [build(tree.top, "active", False, None)]


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
    *,
    services: tuple[str, ...] | None = None,
    waiting: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    target = open_chair(root, address, home)
    published = None
    local = None
    inbox = 0
    mail = 0
    desk = 0
    if target is not None:
        got = status_get(root, home, top, target.address)
        published = got.get("document") if got.get("ok") else None
        local = read_local_status(target)
        inbox = count_inbox(target)
        mail = len(mail_outstanding(target.home, target.address)["mail_unacked_for_me"])
        desk = count_desk(target)
    resolved = target.address if target is not None else address
    left = (waiting or {}).get(resolved) or {}
    doc = published or local or {}
    return {
        "address": resolved,
        "name": name,
        "title": _title(target) or name,
        "kind": kind,
        "sensitive": sensitive,
        "status": status,
        "always_on": always_on,
        "forefront": str(doc.get("forefront") or ""),
        "health": _health(
            published, local, inbox, mail, today,
            sensitive=sensitive,
            owes=status == "active" and _owes(services, target),
            desk=desk,
            waiting=int(left.get("count") or 0),
        ),
    }


def _owes(services: tuple[str, ...] | None, chair: Chair | None) -> bool:
    """True when the chair has signed up to publish a sitrep.

    A registry row says so in its services column. The top nexus, and a chair
    on a plain roster, say so in project.yaml; with nothing to read, it does.
    """
    if services is None:
        listed = _project(chair).get("services")
        if not isinstance(listed, list):
            return True
        services = tuple(str(item) for item in listed)
    return any(item.strip().casefold() == "status" for item in services)


def _health(
    published: dict[str, Any] | None,
    local: dict[str, Any] | None,
    inbox: int,
    mail: int,
    today: date,
    *,
    sensitive: bool = False,
    owes: bool = True,
    desk: int = 0,
    waiting: int = 0,
) -> dict[str, Any]:
    doc = published or local
    updated = _local_day(str((doc or {}).get("updated") or ""))
    age = (today - updated).days if updated else None
    drift = not sensitive and bool(_differs(published, local))
    repo = str((doc or {}).get("repo") or "")
    signals = [
        kind
        for kind, present in (
            ("waiting", waiting > 0),
            ("inbox", inbox > 0),
            ("drift", drift),
            ("mail", mail > 0),
            ("no_sitrep", owes and published is None),
        )
        if present
    ]
    classes = {_CLASS[kind] for kind in signals}
    if "needs_you" in classes:
        state = "needs_you"
    elif "housekeeping" in classes:
        state = "housekeeping"
    elif doc is None and not owes:
        state = "no_publish"
    else:
        state = "up_to_date"
    return {
        "state": state,
        "signals": signals,
        "published": published is not None,
        "local": local is not None,
        "updated": updated.isoformat() if updated else "",
        "age_days": age,
        "drift": drift,
        "repo": repo,
        "dirty": "dirty" in repo.casefold(),
        "inbox": inbox,
        "mail": mail,
        "desk": desk,
        "waiting": waiting,
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
    return [{"address": entry["address"], "name": entry["name"], "title": entry["title"]} for entry in found]


def _project(chair: Chair | None) -> dict[str, Any]:
    if chair is None:
        return {}
    path = chair.project_dir / "project.yaml"
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _title(chair: Chair | None) -> str:
    """The chair's proper name from its project.yaml, or nothing."""
    return str(_project(chair).get("title") or "").strip()


# Settle-pass leftovers ------------------------------------------------------


def _settle_wait(root: Path, home: Path, tree: Tree | None) -> dict[str, dict[str, Any]]:
    """What each nexus's last settle pass could not clear, keyed by the chair it names.

    A pass writes settle-wait.md in the overlay of the chair that ran it, one
    section per chair. A heading that names no chair stays on the nexus that
    holds the file. A sensitive chair shows a count and never its lines.
    """
    found: dict[str, dict[str, Any]] = {}
    if tree is None:
        return found
    seen: dict[str, set[tuple[str, str]]] = {}
    for nexus in tree.nexuses.values():
        holder = open_chair(root, nexus.name.casefold(), home)
        if holder is None:
            continue
        path = local_dir(holder) / "settle-wait.md"
        if not path.is_file():
            continue
        meta, sections = _parse_wait(path.read_text(encoding="utf-8"))
        day = str(meta.get("date") or "")
        held = resolve(tree, holder.address, root_alias=True)
        for heading, items, count in sections:
            located = resolve(tree, heading, root_alias=True) if heading else None
            address = located.address if located else holder.address
            sensitive = bool((located or held) and (located or held).sensitive)
            slot = found.setdefault(address, {"count": 0, "items": [], "passes": []})
            if not any(item["from"] == holder.address for item in slot["passes"]):
                slot["passes"].append({"from": holder.address, "date": day})
            if sensitive:
                slot["count"] = max(slot["count"], count or len(items))
                continue
            if not items:
                slot["count"] += count
            for item in items:
                key = (item.get("surface", ""), item.get("line", ""))
                if key in seen.setdefault(address, set()):
                    continue
                seen[address].add(key)
                kept = {field: item[field] for field in _WAIT_FIELDS if field in item}
                kept.update({"date": day, "from": holder.address})
                if located is None:
                    kept["heading"] = heading
                slot["items"].append(kept)
                slot["count"] += 1
    for slot in found.values():
        slot["passes"].sort(key=lambda item: item["date"], reverse=True)
    return {address: slot for address, slot in found.items() if slot["count"]}


def _parse_wait(text: str) -> tuple[dict[str, Any], list[tuple[str, list[dict[str, str]], int]]]:
    meta: dict[str, Any] = {}
    body = text
    match = _FRONTMATTER.match(text)
    if match:
        try:
            loaded = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            loaded = None
        if isinstance(loaded, dict):
            meta = loaded
        body = text[match.end():]
    sections: list[tuple[str, list[dict[str, str]], int]] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            sections.append((_MARKUP.sub("", stripped[3:]).strip(), [], 0))
            continue
        bullet = _BULLET.match(stripped)
        if not sections or not bullet:
            continue
        heading, items, count = sections[-1]
        key = bullet.group(1).strip().casefold()
        value = bullet.group(2).strip()
        if key == "waiting":
            digits = re.match(r"\d+", value)
            sections[-1] = (heading, items, int(digits.group(0)) if digits else count)
            continue
        # A field that repeats starts the next item.
        if not items or key in items[-1]:
            items.append({})
        items[-1][key] = value
    return meta, [section for section in sections if section[1] or section[2]]


# Signals ------------------------------------------------------------------


class _Guide:
    """Where each fix happens, and what to type there."""

    def __init__(self, root: Path, home: Path, tree: Tree | None, top: str) -> None:
        self.root = root
        self.home = home
        self.named = tree is not None
        self.top = top
        self._folders: dict[str, str] = {}

    def folder(self, address: str | None) -> str:
        if not address:
            return ""
        if address not in self._folders:
            chair = open_chair(self.root, address, self.home)
            self._folders[address] = _shown(self.root, chair.project_dir) if chair else ""
        return self._folders[address]

    def fix(self, kind: str, card: dict[str, Any]) -> dict[str, Any]:
        by = "agent" if _CLASS[kind] == "housekeeping" else "you"
        if not self.named:
            return {"by": by, "command": None, "folder": None, "step": _PLAIN[kind]}
        command, where, step = _NAMED[kind]
        passes = card.get("passes") or []
        places = {
            "chair": self.folder(card.get("address")) or card.get("title") or card.get("node") or "the chair",
            "board": self.folder(card.get("board")),
            "held": self.folder(passes[0]["from"] if passes else card.get("address")),
            "top": self.folder(self.top),
        }
        return {"by": by, "command": command, "folder": places[where], "step": step.format(**places)}


def _shown(root: Path, folder: Path) -> str:
    """A folder as the principal would cd into it: from the bulletin root's parent."""
    try:
        return folder.resolve().relative_to(root.resolve().parent).as_posix()
    except ValueError:
        return folder.name


def _cards(
    index: dict[str, dict[str, Any]],
    boards: dict[str, dict[str, Any]],
    waiting: dict[str, dict[str, Any]],
    guide: _Guide,
) -> list[dict[str, Any]]:
    """One card per thing to clear, carrying every reason and how each one clears.

    A board line is one thing; a chair is another, and a chair's signals split by
    who clears them. Each nexus contributes its own board, so a line is read once.
    """
    cards: dict[tuple, dict[str, Any]] = {}

    def add(key: tuple, kind: str, fields: dict[str, Any]) -> None:
        card = cards.setdefault(key, {"kinds": [], **fields})
        card.update(fields)
        if kind not in card["kinds"]:
            card["kinds"].append(kind)

    for address, board in boards.items():
        sections = board.get("sections") or []
        if sections:
            own = sections[-1]
            for when in ("this_week", "later"):
                for row in own[when]:
                    key = ("line", row["text"], row["node"])
                    fields = {**row, "board": address}
                    if row["days"] is not None and row["days"] < 0:
                        add(key, "date_passed", fields)
                    if row["state"] == "unaccounted":
                        add(key, "unaccounted", fields)
        always_on = zip(board.get("always_on_missing") or [], board.get("always_on_titles") or [])
        for name, title in always_on:
            add(
                ("always_on", address, name), "always_on",
                {"node": name, "title": title, "address": None, "sensitive": False, "board": address},
            )
    for entry in index.values():
        health = entry["health"]
        base = {
            "address": entry["address"],
            "node": entry["name"],
            "title": entry["title"],
            "sensitive": entry["sensitive"],
        }
        for kind in health["signals"]:
            fields = dict(base)
            if kind in ("inbox", "mail"):
                fields[kind] = health[kind]
            elif kind == "waiting":
                left = waiting.get(entry["address"]) or {}
                fields.update(waiting=health["waiting"], items=left.get("items") or [], passes=left.get("passes") or [])
            add(("chair", entry["address"], _CLASS[kind]), kind, fields)
    items = list(cards.values())
    for card in items:
        card["kinds"].sort(key=_ORDER.index)
        card["kind"] = card["kinds"][0]
        card["class"] = _CLASS[card["kind"]]
        card["fixes"] = [{"kind": kind, **guide.fix(kind, card)} for kind in card["kinds"]]
    items.sort(key=lambda card: (_ORDER.index(card["kind"]), card.get("days") or 0))
    return items


def _rank_chairs(index: dict[str, dict[str, Any]], cards: list[dict[str, Any]]) -> None:
    """A chair's dot shows the most urgent class among the cards about it."""
    for card in cards:
        entry = index.get(card.get("address") or card.get("board") or "")
        if entry is None or card["class"] not in _RANK:
            continue
        health = entry["health"]
        if _RANK[card["class"]] > _RANK.get(health["state"], 0):
            health["state"] = card["class"]


def _within(card: dict[str, Any], under: set[str]) -> bool:
    address = card.get("address")
    return (address in under) if address else (card.get("board") in under)


def _housekeeping(chores: list[dict[str, Any]], guide: _Guide, view: str) -> dict[str, Any]:
    """Everything an agent can clear under the nexus in view, as one line and one command."""
    chairs = {card["address"] for card in chores if card.get("address")}
    if guide.named:
        folder = guide.folder(view)
        fix = {
            "by": "agent",
            "command": "/settle-pass all",
            "folder": folder,
            "step": f"Run /settle-pass all in {folder}. It settles every chair under it and leaves what it cannot clear in settle-wait.md.",
        }
    else:
        fix = {"by": "agent", "command": None, "folder": None, "step": "Settle each chair listed."}
    return {"count": len(chairs), "cards": chores, "fix": fix}


# The board ----------------------------------------------------------------


def _board(
    root: Path,
    home: Path,
    tree: Tree | None,
    view: str,
    today: date,
    titles: dict[str, str],
) -> dict[str, Any]:
    snap = now_view(root, home, view, read_only=True)
    if snap.get("error") == "missing_now":
        return {"nexus": view, "missing": True, "sections": [], "always_on_missing": [], "always_on_titles": []}
    if not snap.get("ok"):
        return {
            "nexus": view, "missing": True, "sections": [],
            "always_on_missing": [], "always_on_titles": [], "error": snap.get("error"),
        }
    states = {(row["text"], row["node"]): row["state"] for row in snap.get("reconcile") or []}
    sections: list[dict[str, Any]] = []
    focus = snap.get("focus")
    if focus:
        name = str(focus.get("node") or "")
        sensitive = _sensitive_name(tree, name)
        sections.append(_section(tree, titles, name, sensitive, focus, states, today))
    view_sensitive = _sensitive_name(tree, view)
    sections.append(_section(tree, titles, view, view_sensitive, snap.get("now") or {}, states, today))
    always_on = [str(name) for name in snap.get("always_on_missing") or []]
    return {
        "nexus": view,
        "missing": False,
        "sections": sections,
        "always_on_missing": always_on,
        "always_on_titles": [_titled(tree, titles, name) for name in always_on],
    }


def _section(
    tree: Tree | None,
    titles: dict[str, str],
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
                "title": titles.get(located.address, node) if located else node,
                "address": located.address if located else None,
                "due": row.get("due"),
                "days": (due - today).days if due else None,
                "state": states.get((row["text"], node)) if node else None,
                "sensitive": sensitive or bool(located and located.sensitive),
            })
        return out

    return {
        "name": name,
        "title": _titled(tree, titles, name),
        "sensitive": sensitive,
        "updated": parsed.get("updated") or "",
        "this_week": items(parsed.get("this_week") or []),
        "later": items(parsed.get("later") or []),
    }


def _titled(tree: Tree | None, titles: dict[str, str], name: str) -> str:
    located = resolve(tree, name, root_alias=True) if tree is not None and name else None
    return titles.get(located.address, name) if located else name


def _next(board: dict[str, Any]) -> dict[str, Any] | None:
    for section in board.get("sections") or []:
        if section["this_week"]:
            return {**section["this_week"][0], "board": section["name"]}
    return None


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
