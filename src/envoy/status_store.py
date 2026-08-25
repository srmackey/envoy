from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from envoy.mapfile import known_chairs, load_project


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _path(home: Path, name: str) -> Path:
    return home / "status" / f"{name}.json"


def _subscribed(root: Path, chair: str, service: str) -> bool:
    proj = load_project(root, chair)
    services = (proj or {}).get("services") or []
    return service in services


def status_put(
    root: Path,
    home: Path,
    chair: str,
    forefront: str,
    where_i_left_off: list[str],
    next_steps: list[str],
    open_loops: list[str],
    repo: str | None = None,
) -> dict[str, Any]:
    if chair not in known_chairs(root):
        return {"ok": False, "error": "unknown_chair"}
    if not _subscribed(root, chair, "status"):
        return {"ok": False, "error": "not_subscribed"}
    path = _path(home, chair)
    version = 1
    if path.is_file():
        prev = json.loads(path.read_text(encoding="utf-8"))
        version = int(prev.get("version") or 0) + 1
    document: dict[str, Any] = {
        "node": chair,
        "author": chair,
        "version": version,
        "updated": _now(),
        "forefront": forefront,
        "where_i_left_off": list(where_i_left_off),
        "next_steps": list(next_steps),
        "open_loops": list(open_loops),
    }
    if repo:
        document["repo"] = repo
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return {"ok": True, "document": document}


def status_get(
    root: Path,
    home: Path,
    chair: str,
    node: str | None = None,
) -> dict[str, Any]:
    if chair not in known_chairs(root):
        return {"ok": False, "error": "unknown_chair"}
    target = node or chair
    if chair != "nexus" and target != chair:
        return {"ok": False, "error": "forbidden"}
    path = _path(home, target)
    if not path.is_file():
        return {"ok": False, "error": "missing_status"}
    document = json.loads(path.read_text(encoding="utf-8"))
    return {"ok": True, "document": document}
