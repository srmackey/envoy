"""Read-only snapshot for the local page.

The page re-reads the board, the roster, and published sitreps. It also reads
the local status file and pending inbox files. It never lists mail notes, so
a refresh does not mark a note seen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from envoy.address import load_tree, resolve
from envoy.mapfile import Chair, map_list, open_chair
from envoy.notes_store import mail_outstanding
from envoy.now import now_view
from envoy.status_store import status_get

_SKIP_INBOX = {"_log.md", "README.md"}
_FIELDS = (
    "forefront",
    "where_i_left_off",
    "next_steps",
    "open_loops",
    "repo",
)


def board_snapshot(root: Path, home: Path, chair: str | None = None) -> dict[str, Any]:
    chair = chair or _default_chair(root)
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    snap = now_view(root, home, caller.address, read_only=True)
    if snap.get("error") == "missing_now":
        snap = {
            "ok": True,
            "now": {"updated": "", "this_week": [], "later": []},
            "missing_board": True,
            "reconcile": [],
            "forefronts": [],
            "always_on_missing": [],
        }
    elif not snap.get("ok"):
        return snap
    if "mail_unacked" not in snap:
        notice = mail_outstanding(caller.home, caller.address)
        snap["mail_unacked"] = len(notice["mail_unacked_for_me"])
    snap["chair"] = caller.address
    snap["parent"] = _parent(root, caller)
    snap["entries"] = _entries(root, caller.address)
    snap["inbox_count"] = count_inbox(caller)
    snap["self"] = _files(root, home, caller)
    return snap


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
    return {
        "ok": True,
        "address": target.address,
        "sensitive": _sensitive(root, target.address),
        "published": published,
        "local": local,
        "diverged": _diverged(published, local),
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


def _default_chair(root: Path) -> str:
    tree = load_tree(root)
    if tree is None:
        return "nexus"
    return tree.top.name


def _parent(root: Path, caller: Chair) -> str | None:
    if caller.legacy or not caller.is_nexus or caller.is_root:
        return None
    tree = load_tree(root)
    if tree is None:
        return None
    nexus = tree.nexuses.get(caller.address)
    if nexus is None or not nexus.parent:
        return None
    return nexus.parent.casefold()


def _entries(root: Path, chair: str) -> list[dict[str, Any]]:
    listed = map_list(root, chair)
    entries = [dict(item) for item in listed.get("entries") or []]
    tree = load_tree(root)
    for entry in entries:
        name = str(entry.get("name") or "")
        if tree is None:
            entry["sensitive"] = False
            entry["opens"] = False
            continue
        located = resolve(tree, name, root_alias=True)
        entry["sensitive"] = bool(located and located.sensitive)
        entry["opens"] = bool(located and located.is_nexus) or entry.get("kind") == "nexus"
    return entries


def _files(root: Path, home: Path, caller: Chair) -> dict[str, Any]:
    got = status_get(root, home, caller.address)
    published = got.get("document") if got.get("ok") else None
    local = read_local_status(caller)
    return {
        "published": published,
        "local": local,
        "diverged": _diverged(published, local),
        "inbox_count": count_inbox(caller),
    }


def _sensitive(root: Path, address: str) -> bool:
    tree = load_tree(root)
    if tree is None:
        return False
    located = resolve(tree, address, root_alias=True)
    return bool(located and located.sensitive)


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
        if stripped.startswith("- "):
            current.append(stripped[2:].strip())
        else:
            current.append(stripped)
    forefront = sections["forefront"]
    return {
        "updated": updated,
        "repo": repo,
        "forefront": forefront[0] if forefront else "",
        "where_i_left_off": sections["where i left off"],
        "next_steps": sections["next steps"],
        "open_loops": sections["open loops"],
    }


def _norm_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = " ".join(value.split())
        return [text] if text else []
    if not isinstance(value, list):
        return []
    return [" ".join(str(item).split()) for item in value if str(item).strip()]


def _diverged(published: dict[str, Any] | None, local: dict[str, Any] | None) -> bool:
    if not published or not local:
        return False
    return any(_norm_list(published.get(field)) != _norm_list(local.get(field)) for field in _FIELDS)
