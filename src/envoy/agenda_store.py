"""The agenda: one calendar and one task list for the whole bulletin.

Rows live in the root nexus's store, whatever chair posts them. A row with a
`due` date is on the calendar. A row without one is a task. Any subscribed
chair may post. A chair may change or close only rows it authored. The root
nexus may change or close any row, and only the root reorders the task list.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from envoy.address import load_tree
from envoy.mapfile import Chair, load_project, open_chair

BUCKETS = ("overdue", "due_soon", "before_sunday", "next_week", "later")
SCOPES = {"all", "mine"}
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _store(root: Path, default_home: Path) -> Path:
    """The one agenda folder: the root nexus's `_envoy/agenda/`, or ENVOY_HOME without nexus.md."""
    tree = load_tree(root)
    home = default_home if tree is None else tree.top.folder / "_envoy"
    return home / "agenda"


def _subscribed(root: Path, chair: str) -> bool:
    proj = load_project(root, chair)
    services = (proj or {}).get("services") or []
    return "agenda" in services


def _rows(folder: Path) -> list[dict[str, Any]]:
    if not folder.is_dir():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]


def _load(folder: Path, item_id: str) -> dict[str, Any] | None:
    name = str(item_id or "").strip()
    if not re.fullmatch(r"[0-9a-f]{32}", name):
        return None
    path = folder / f"{name}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save(folder: Path, row: dict[str, Any]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{row['id']}.json").write_text(json.dumps(row, indent=2), encoding="utf-8")


def _day(value: str) -> date:
    if not _DAY.match(value):
        raise ValueError
    return date.fromisoformat(value)


def _window(due: str | None, until: str | None) -> tuple[str | None, str | None] | str:
    """Check a date pair. Returns the pair, or an error token."""
    due = (due or "").strip() or None
    until = (until or "").strip() or None
    if due is None:
        return "invalid_window" if until is not None else (None, None)
    try:
        first = _day(due)
        last = _day(until) if until is not None else first
    except ValueError:
        return "invalid_date"
    if last < first:
        return "invalid_window"
    return due, until


def _is_task(row: dict[str, Any]) -> bool:
    return not row.get("due")


def _open(row: dict[str, Any]) -> bool:
    return not row.get("closed")


def _bottom(folder: Path) -> int:
    ranks = [int(r["rank"]) for r in _rows(folder) if _open(r) and _is_task(r) and r.get("rank") is not None]
    return (max(ranks) + 1) if ranks else 1


def _may_edit(caller: Chair, row: dict[str, Any]) -> bool:
    return caller.is_root or str(row.get("author") or "").casefold() == caller.address.casefold()


def agenda_post(
    root: Path,
    home: Path,
    chair: str,
    text: str,
    due: str | None = None,
    until: str | None = None,
) -> dict[str, Any]:
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    if not _subscribed(root, caller.address):
        return {"ok": False, "error": "not_subscribed"}
    if not str(text or "").strip():
        return {"ok": False, "error": "invalid_payload"}
    window = _window(due, until)
    if isinstance(window, str):
        return {"ok": False, "error": window}
    folder = _store(root, home)
    stamp = _now()
    row: dict[str, Any] = {
        "id": uuid.uuid4().hex,
        "kind": "agenda",
        "author": caller.address,
        "created": stamp,
        "updated": stamp,
        "text": str(text).strip(),
        "due": window[0],
        "until": window[1],
        "rank": None if window[0] else _bottom(folder),
        "closed": None,
    }
    _save(folder, row)
    return {"ok": True, "item": row}


def agenda_update(
    root: Path,
    home: Path,
    chair: str,
    item_id: str,
    text: str | None = None,
    due: str | None = None,
    until: str | None = None,
) -> dict[str, Any]:
    """Change a row. An omitted field is left alone. An empty `due` clears the date."""
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    folder = _store(root, home)
    row = _load(folder, item_id)
    if row is None:
        return {"ok": False, "error": "missing_item"}
    if not _may_edit(caller, row):
        return {"ok": False, "error": "not_author"}
    if not _open(row):
        return {"ok": False, "error": "closed"}
    if text is not None:
        if not text.strip():
            return {"ok": False, "error": "invalid_payload"}
        row["text"] = text.strip()
    if due is not None or until is not None:
        new_due = row.get("due") if due is None else due
        new_until = row.get("until") if until is None else until
        if due is not None and not due.strip() and until is None:
            new_until = None
        window = _window(new_due, new_until)
        if isinstance(window, str):
            return {"ok": False, "error": window}
        was_task = _is_task(row)
        row["due"], row["until"] = window
        if row["due"]:
            row["rank"] = None
        elif not was_task:
            row["rank"] = _bottom(folder)
    row["updated"] = _now()
    _save(folder, row)
    return {"ok": True, "item": row}


def agenda_close(root: Path, home: Path, chair: str, item_id: str) -> dict[str, Any]:
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    folder = _store(root, home)
    row = _load(folder, item_id)
    if row is None:
        return {"ok": False, "error": "missing_item"}
    if not _may_edit(caller, row):
        return {"ok": False, "error": "not_author"}
    if _open(row):
        row["closed"] = {"chair": caller.address, "time": _now()}
        row["rank"] = None
        row["updated"] = row["closed"]["time"]
        _save(folder, row)
    return {"ok": True, "item": row}


def agenda_reorder(root: Path, home: Path, chair: str, order: list[str]) -> dict[str, Any]:
    """Root only. The named tasks go to the top in that order. The rest keep their order below."""
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    if not caller.is_root:
        return {"ok": False, "error": "root_only"}
    folder = _store(root, home)
    tasks = _ordered_tasks(_rows(folder))
    by_id = {row["id"]: row for row in tasks}
    ids = [str(i).strip() for i in order]
    if not ids or len(set(ids)) != len(ids):
        return {"ok": False, "error": "invalid_payload"}
    missing = [i for i in ids if i not in by_id]
    if missing:
        return {"ok": False, "error": "not_a_task", "items": missing}
    named = set(ids)
    head = [by_id[i] for i in ids]
    rest = [row for row in tasks if row["id"] not in named]
    stamp = _now()
    for rank, row in enumerate(head + rest, start=1):
        if row.get("rank") != rank:
            row["rank"] = rank
            row["updated"] = stamp
            _save(folder, row)
    return {"ok": True, "tasks": head + rest}


def _ordered_tasks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks = [r for r in rows if _open(r) and _is_task(r)]
    return sorted(tasks, key=lambda r: (r.get("rank") is None, r.get("rank") or 0, r.get("created") or ""))


def _bucket(row: dict[str, Any], today: date) -> str:
    first = date.fromisoformat(row["due"])
    last = date.fromisoformat(row["until"]) if row.get("until") else first
    if last < today:
        return "overdue"
    start = max(first, today)
    tomorrow = today + timedelta(days=1)
    this_sunday = today + timedelta(days=(6 - today.weekday()))
    next_sunday = this_sunday + timedelta(days=7)
    if start <= tomorrow:
        return "due_soon"
    if start <= this_sunday:
        return "before_sunday"
    if start <= next_sunday:
        return "next_week"
    return "later"


def agenda_list(
    root: Path,
    home: Path,
    chair: str,
    scope: str = "all",
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Read the agenda. Never closes or acks a row."""
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    if scope not in SCOPES:
        return {"ok": False, "error": "invalid_payload"}
    day = today or date.today()
    rows = [r for r in _rows(_store(root, home)) if _open(r)]
    if scope == "mine":
        rows = [r for r in rows if str(r.get("author") or "").casefold() == caller.address.casefold()]
    calendar: dict[str, list[dict[str, Any]]] = {name: [] for name in BUCKETS}
    dated = sorted(
        (r for r in rows if not _is_task(r)),
        key=lambda r: (r["due"], r.get("created") or ""),
    )
    for row in dated:
        calendar[_bucket(row, day)].append(row)
    tasks = _ordered_tasks(rows)
    following = next((calendar[name][0] for name in BUCKETS if calendar[name]), None)
    counts = {name: len(calendar[name]) for name in BUCKETS}
    counts["tasks"] = len(tasks)
    return {
        "ok": True,
        "scope": scope,
        "today": day.isoformat(),
        "counts": counts,
        "next": following,
        "calendar": calendar,
        "tasks": tasks,
    }
