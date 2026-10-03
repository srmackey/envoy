from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from envoy.address import load_tree
from envoy.mapfile import Chair, load_project, nexus_homes, open_chair

GATES = {"deliver", "hold", "foul"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mail_dir(home: Path) -> Path:
    path = home / "mail"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _path(home: Path, note_id: str) -> Path:
    return _mail_dir(home) / f"{note_id}.json"


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


def _names_match(caller: Chair, stored: object) -> bool:
    other = str(stored or "").strip().casefold()
    if not other:
        return False
    address = caller.address.casefold()
    if address == other:
        return True
    if caller.is_root and other == "nexus":
        return True
    return address.endswith("/" + other) or other.endswith("/" + address)


def _can_see(caller: Chair, note: dict[str, Any]) -> bool:
    if caller.is_root or (caller.legacy and caller.address == "nexus"):
        return True
    return _names_match(caller, note.get("author")) or _names_match(
        caller, note.get("intended_for")
    )


def _public(note: dict[str, Any], caller: Chair) -> dict[str, Any]:
    item = dict(note)
    if not (caller.is_root or (caller.legacy and caller.address == "nexus")):
        item.pop("gate", None)
        item.pop("gate_note", None)
    return item


def _note_file(home: Path, note_id: str) -> Path:
    return home / "mail" / f"{note_id}.json"


def _write_note(root: Path, default_home: Path, note: dict[str, Any]) -> None:
    homes: list[Path] = []
    if load_tree(root) is None:
        homes = [default_home]
    else:
        for who in (note.get("author"), note.get("intended_for")):
            ref = open_chair(root, str(who or ""), default_home)
            if ref is not None and ref.home not in homes:
                homes.append(ref.home)
        if not homes:
            homes = [default_home]
    for home in homes:
        _save(home, note)


def _homes_with_note(root: Path, default_home: Path, note_id: str) -> list[Path]:
    if load_tree(root) is None:
        homes = [default_home]
    else:
        homes = nexus_homes(root)
    return [home for home in homes if _note_file(home, note_id).is_file()]


def _parse_time(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def _expired(note: dict[str, Any], now: datetime) -> bool:
    ack = note.get("ack") or None
    if not ack:
        return False
    if note.get("gate") in {"hold", "foul"}:
        return False
    stamp = ack.get("time")
    if not stamp:
        return False
    return now - _parse_time(str(stamp)) > timedelta(days=14)


def _iter_open_mail(home: Path, now: datetime) -> list[dict[str, Any]]:
    folder = home / "mail"
    if not folder.is_dir():
        return []
    notes: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")):
        note = json.loads(path.read_text(encoding="utf-8"))
        if _expired(note, now):
            continue
        notes.append(note)
    return notes


def mail_outstanding(
    home: Path,
    chair: str,
    *,
    now: datetime | None = None,
) -> dict[str, list[str]]:
    """Chair-scoped mail notice: unacked for me, and my authored notes that carry ack."""
    current = now or datetime.now(timezone.utc)
    unacked: list[str] = []
    acked_authored: list[str] = []
    for note in _iter_open_mail(home, current):
        note_id = str(note["id"])
        if _string_match(chair, note.get("intended_for")) and not (note.get("ack") or None):
            unacked.append(note_id)
        if _string_match(chair, note.get("author")) and (note.get("ack") or None):
            acked_authored.append(note_id)
    return {
        "mail_unacked_for_me": unacked,
        "mail_acked_authored": acked_authored,
    }


def with_mail_notice(
    result: dict[str, Any],
    home: Path,
    chair: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Merge outstanding-mail ids into any tool result."""
    merged = dict(result)
    merged.update(mail_outstanding(home, chair, now=now))
    return merged


def _string_match(caller: str, stored: object) -> bool:
    other = str(stored or "").strip().casefold()
    left = caller.strip().casefold()
    if not other:
        return False
    if left == other:
        return True
    if left == "nexus" and other == "nexus":
        return True
    return left.endswith("/" + other) or other.endswith("/" + left)


def note_post(
    root: Path,
    home: Path,
    chair: str,
    intended_for: str,
    inbox: str,
    why: str,
) -> dict[str, Any]:
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    if not _subscribed(root, caller.address, "mail"):
        return {"ok": False, "error": "not_subscribed"}
    dest = open_chair(root, intended_for, home)
    note = {
        "id": uuid.uuid4().hex,
        "kind": "mail",
        "author": caller.address,
        "created": _now(),
        "ack": None,
        "intended_for": dest.address if dest is not None else intended_for,
        "inbox": inbox,
        "why": why,
    }
    _write_note(root, home, note)
    return {"ok": True, "note": _public(note, caller)}


def note_list(
    root: Path,
    home: Path,
    chair: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    current = now or datetime.now(timezone.utc)
    notes: list[dict[str, Any]] = []
    for note in _iter_open_mail(caller.home, current):
        if not _can_see(caller, note):
            continue
        # Listing as the intended chair is awareness: ack shown. A nexus
        # listing other chairs' mail does not match intended_for and is not touched.
        if _names_match(caller, note.get("intended_for")) and not (note.get("ack") or None):
            note["ack"] = {"chair": caller.address, "time": _now(), "action": "shown"}
            _write_note(root, home, note)
        notes.append(_public(note, caller))
    return {"ok": True, "notes": notes}


def note_ack(
    root: Path,
    home: Path,
    chair: str,
    note_id: str,
    action: str,
) -> dict[str, Any]:
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    if not str(action).strip():
        return {"ok": False, "error": "invalid_payload"}
    homes = _homes_with_note(root, home, note_id)
    if not homes:
        return {"ok": False, "error": "missing_note"}
    note = _load(homes[0], note_id)
    if note is None:
        return {"ok": False, "error": "missing_note"}
    if not _can_see(caller, note):
        return {"ok": False, "error": "forbidden"}
    note["ack"] = {"chair": caller.address, "time": _now(), "action": action}
    _write_note(root, home, note)
    return {"ok": True, "note": _public(note, caller)}


def note_gate(
    root: Path,
    home: Path,
    chair: str,
    note_id: str,
    gate: str,
    gate_note: str | None = None,
) -> dict[str, Any]:
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    if not caller.is_root:
        return {"ok": False, "error": "nexus_only"}
    if gate not in GATES:
        return {"ok": False, "error": "invalid_payload"}
    homes = _homes_with_note(root, home, note_id)
    if not homes:
        return {"ok": False, "error": "missing_note"}
    note = _load(homes[0], note_id)
    if note is None:
        return {"ok": False, "error": "missing_note"}
    note["gate"] = gate
    if gate_note:
        note["gate_note"] = gate_note
    else:
        note.pop("gate_note", None)
    _write_note(root, home, note)
    return {"ok": True, "note": note}


def note_remove(
    root: Path,
    home: Path,
    chair: str,
    note_id: str,
) -> dict[str, Any]:
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    homes = _homes_with_note(root, home, note_id)
    if not homes:
        return {"ok": False, "error": "missing_note"}
    note = _load(homes[0], note_id)
    if note is None:
        return {"ok": False, "error": "missing_note"}
    if not _names_match(caller, note.get("author")):
        return {"ok": False, "error": "not_author"}
    for found in homes:
        _note_file(found, note_id).unlink(missing_ok=True)
    return {"ok": True, "id": note_id}
