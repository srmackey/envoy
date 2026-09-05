from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from envoy.mapfile import known_chairs, load_project


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _syos_dir(home: Path) -> Path:
    path = home / "syos"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _path(home: Path, note_id: str) -> Path:
    return _syos_dir(home) / f"{note_id}.json"


def _subscribed(root: Path, chair: str, service: str) -> bool:
    proj = load_project(root, chair)
    services = (proj or {}).get("services") or []
    return service in services


def _load(home: Path, note_id: str) -> dict[str, Any] | None:
    path = _path(home, note_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _save(home: Path, note: dict[str, Any]) -> None:
    path = _path(home, str(note["id"]))
    path.write_text(json.dumps(note, indent=2), encoding="utf-8")


def _can_see(chair: str, note: dict[str, Any]) -> bool:
    return note.get("author") == chair


def _parse_time(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def _expired(note: dict[str, Any], now: datetime) -> bool:
    ack = note.get("ack") or None
    if not ack:
        return False
    stamp = ack.get("time")
    if not stamp:
        return False
    return now - _parse_time(str(stamp)) > timedelta(days=14)


def syos_post(
    root: Path,
    home: Path,
    chair: str,
    body: str,
) -> dict[str, Any]:
    if chair not in known_chairs(root):
        return {"ok": False, "error": "unknown_chair"}
    if not _subscribed(root, chair, "syos"):
        return {"ok": False, "error": "not_subscribed"}
    text = str(body).strip()
    if not text:
        return {"ok": False, "error": "invalid_payload"}
    note = {
        "id": uuid.uuid4().hex,
        "kind": "syos",
        "author": chair,
        "created": _now(),
        "ack": None,
        "intended_for": chair,
        "body": text,
    }
    _save(home, note)
    return {"ok": True, "note": dict(note)}


def syos_list(
    root: Path,
    home: Path,
    chair: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    if chair not in known_chairs(root):
        return {"ok": False, "error": "unknown_chair"}
    current = now or datetime.now(timezone.utc)
    notes: list[dict[str, Any]] = []
    folder = home / "syos"
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            note = json.loads(path.read_text(encoding="utf-8"))
            if _expired(note, current):
                continue
            if _can_see(chair, note):
                notes.append(dict(note))
    return {"ok": True, "notes": notes}


def syos_ack(
    root: Path,
    home: Path,
    chair: str,
    note_id: str,
    action: str,
) -> dict[str, Any]:
    if chair not in known_chairs(root):
        return {"ok": False, "error": "unknown_chair"}
    if not str(action).strip():
        return {"ok": False, "error": "invalid_payload"}
    note = _load(home, note_id)
    if note is None:
        return {"ok": False, "error": "missing_note"}
    if not _can_see(chair, note):
        return {"ok": False, "error": "forbidden"}
    note["ack"] = {"chair": chair, "time": _now(), "action": action}
    _save(home, note)
    return {"ok": True, "note": dict(note)}


def syos_remove(
    root: Path,
    home: Path,
    chair: str,
    note_id: str,
) -> dict[str, Any]:
    if chair not in known_chairs(root):
        return {"ok": False, "error": "unknown_chair"}
    note = _load(home, note_id)
    if note is None:
        return {"ok": False, "error": "missing_note"}
    if note.get("author") != chair:
        return {"ok": False, "error": "not_author"}
    _path(home, note_id).unlink()
    return {"ok": True, "id": note_id}
