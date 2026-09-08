from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from envoy.notes_store import note_list
from envoy.status_store import status_get

LINE_RE = re.compile(r"\*\*(.+?)\*\*\s*·\s*due:\s*(\S+)\s*·\s*node:\s*(\S+)")
ALWAYS_ON = ("family", "career")


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
        return "unaccounted", None
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


def now_view(root: Path, home: Path, chair: str) -> dict[str, Any]:
    path = root / "NOW.md"
    if not path.is_file():
        return {"ok": False, "error": "missing_now"}
    parsed = parse_now(path.read_text(encoding="utf-8"))
    result: dict[str, Any] = {"ok": True, "now": parsed}
    if chair != "nexus":
        return result
    reconcile: list[dict[str, Any]] = []
    for section in ("this_week", "later"):
        for item in parsed[section]:
            node = item["node"]
            if node is None:
                continue
            got = status_get(root, home, chair="nexus", node=node)
            document = got.get("document") if got.get("ok") else None
            state, forefront = _state(item["text"], document)
            reconcile.append({
                "text": item["text"],
                "node": node,
                "section": section,
                "state": state,
                "forefront": forefront,
            })
    forefronts: list[dict[str, Any]] = []
    status_dir = home / "status"
    if status_dir.is_dir():
        for file in sorted(status_dir.glob("*.json")):
            document = json.loads(file.read_text(encoding="utf-8"))
            row = {
                "node": document.get("node"),
                "forefront": document.get("forefront"),
                "updated": document.get("updated"),
            }
            if document.get("repo"):
                row["repo"] = document["repo"]
            forefronts.append(row)
    week_nodes = {item["node"] for item in parsed["this_week"] if item["node"]}
    mail = note_list(root, home, chair="nexus")
    result["reconcile"] = reconcile
    result["forefronts"] = forefronts
    result["mail"] = mail.get("notes") or []
    result["always_on_missing"] = [name for name in ALWAYS_ON if name not in week_nodes]
    return result
