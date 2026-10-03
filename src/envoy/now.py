from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from envoy.address import Nexus, load_tree
from envoy.mapfile import open_chair
from envoy.notes_store import note_list
from envoy.status_store import status_get

LINE_RE = re.compile(r"\*\*(.+?)\*\*\s*·\s*due:\s*(\S+)\s*·\s*node:\s*(\S+)")


def load_always_on(root: Path) -> list[str]:
    path = root / "always-on.yaml"
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return []
    if isinstance(data, list):
        names = data
    elif isinstance(data, dict):
        names = data.get("always_on") or data.get("chairs") or []
    else:
        return []
    if not isinstance(names, list):
        return []
    return [str(n).strip() for n in names if str(n).strip()]


def _norm(text: str) -> str:
    return " ".join(text.split())


def _parse_items(block: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for match in LINE_RE.finditer(block):
        due_raw = match.group(2)
        node_raw = match.group(3)
        items.append({
            "text": match.group(1),
            "due": None if due_raw == "none" else due_raw,
            "node": None if node_raw == "none" else node_raw,
        })
    return items


def parse_now(text: str) -> dict[str, Any]:
    updated = ""
    for line in text.splitlines():
        if line.startswith("updated:"):
            updated = line.split(":", 1)[1].strip()
            break
    this_week = ""
    later = ""
    if "## This week" in text:
        _, rest = text.split("## This week", 1)
        if "## Later" in rest:
            this_week, later = rest.split("## Later", 1)
        else:
            this_week = rest
    elif "## Later" in text:
        later = text.split("## Later", 1)[1]
    return {
        "updated": updated,
        "this_week": _parse_items(this_week),
        "later": _parse_items(later),
    }


def _state(board_text: str, document: dict[str, Any] | None) -> tuple[str, str | None]:
    if document is None:
        return "no_trail", None
    forefront = str(document.get("forefront") or "")
    trail = " ".join(str(part) for part in (document.get("where_i_left_off") or []))
    repo = str(document.get("repo") or "")
    board = _norm(board_text)
    if _norm(forefront) == board:
        return "current", forefront
    if board and board in _norm(trail):
        return "accounted", forefront
    if board and board in _norm(repo):
        return "satisfied", forefront
    return "unaccounted", forefront


def board_file(folder: Path) -> Path | None:
    focus = folder / "FOCUS.md"
    if focus.is_file():
        return focus
    legacy = folder / "NOW.md"
    if legacy.is_file():
        return legacy
    return None


def _read_board(folder: Path) -> dict[str, Any] | None:
    path = board_file(folder)
    if path is None:
        return None
    return parse_now(path.read_text(encoding="utf-8"))


def _week_nodes(parsed: dict[str, Any]) -> set[str]:
    return {item["node"].casefold() for item in parsed["this_week"] if item["node"]}


def _reconcile(
    root: Path,
    home: Path,
    chair: str,
    parsed: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section in ("this_week", "later"):
        for item in parsed[section]:
            node = item["node"]
            if node is None:
                continue
            got = status_get(root, home, chair=chair, node=node)
            document = got.get("document") if got.get("ok") else None
            state, forefront = _state(item["text"], document)
            rows.append({
                "text": item["text"],
                "node": node,
                "section": section,
                "state": state,
                "forefront": forefront,
            })
    return rows


def _missing(names: list[str], parsed: dict[str, Any]) -> list[str]:
    week = _week_nodes(parsed)
    return [name for name in names if name.casefold() not in week]


def _always_on_rows(nexus: Nexus) -> list[str]:
    return [node.name for node in nexus.nodes if node.always_on]


def now_view(root: Path, home: Path, chair: str) -> dict[str, Any]:
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    tree = None if caller.legacy else load_tree(root)
    board_dir = root if caller.legacy else caller.home.parent
    parsed = _read_board(board_dir)
    if parsed is None:
        return {"ok": False, "error": "missing_now"}
    result: dict[str, Any] = {"ok": True, "now": parsed}
    if not caller.is_nexus:
        return result
    nexus = None if tree is None else tree.nexuses.get(caller.address)
    borrowed: dict[str, Any] | None = None
    child: Nexus | None = None
    if nexus is not None and nexus.focus and tree is not None:
        child = tree.nexuses.get(nexus.focus.casefold())
        if child is not None:
            borrowed = _read_board(child.folder)
            if borrowed is not None:
                result["focus"] = {"node": child.name, **borrowed}
        else:
            for node in nexus.nodes:
                if node.name.casefold() != nexus.focus.casefold() or node.kind == "nexus":
                    continue
                folder = nexus.folder / node.path
                borrowed = _read_board(folder)
                if borrowed is not None:
                    result["focus"] = {"node": node.name, **borrowed}
                break
    reconcile = _reconcile(root, home, chair, parsed)
    if borrowed is not None:
        reconcile = _reconcile(root, home, chair, borrowed) + reconcile
    forefronts: list[dict[str, Any]] = []
    status_dir = (home if caller.legacy else caller.home) / "status"
    focus_name = nexus.focus.casefold() if nexus is not None and nexus.focus else None
    direct: set[str] = set()
    if nexus is not None:
        direct = {
            node.name.casefold()
            for node in nexus.nodes
            if node.name.casefold() != focus_name
        }
    if status_dir.is_dir():
        for file in sorted(status_dir.glob("*.json")):
            document = json.loads(file.read_text(encoding="utf-8"))
            node_name = str(document.get("node") or "")
            if nexus is not None and not _is_direct(node_name, caller.address, direct):
                continue
            row = {
                "node": document.get("node"),
                "forefront": document.get("forefront"),
                "updated": document.get("updated"),
            }
            if document.get("repo"):
                row["repo"] = document["repo"]
            forefronts.append(row)
    missing: list[str] = []
    if caller.legacy or nexus is None:
        missing = _missing(load_always_on(root), parsed)
    else:
        if child is not None and borrowed is not None:
            missing.extend(_missing(_always_on_rows(child), borrowed))
        missing.extend(_missing(_always_on_rows(nexus), parsed))
    mail = note_list(root, home, chair=chair)
    result["reconcile"] = reconcile
    result["forefronts"] = forefronts
    result["mail"] = mail.get("notes") or []
    result["always_on_missing"] = missing
    return result


def _is_direct(node_name: str, nexus_name: str, names: set[str]) -> bool:
    node = node_name.casefold()
    if node in names:
        return True
    prefix = nexus_name.casefold() + "/"
    return node.startswith(prefix) and node[len(prefix):] in names
