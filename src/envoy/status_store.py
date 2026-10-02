from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from envoy.mapfile import load_project, open_chair


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
    ref = open_chair(root, chair, home)
    if ref is None:
        return {"ok": False, "error": "unknown_chair"}
    if not _subscribed(root, ref.address, "status"):
        return {"ok": False, "error": "not_subscribed"}
    path = _path(ref.home, ref.slug)
    version = 1
    if path.is_file():
        prev = json.loads(path.read_text(encoding="utf-8"))
        version = int(prev.get("version") or 0) + 1
    document: dict[str, Any] = {
        "node": ref.address,
        "author": ref.address,
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
    caller = open_chair(root, chair, home)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    target = open_chair(root, node or chair, home)
    if target is None:
        return {"ok": False, "error": "unknown_chair"}
    if caller.address != target.address:
        if not caller.is_nexus:
            return {"ok": False, "error": "forbidden"}
        try:
            target.project_dir.resolve().relative_to(caller.project_dir.resolve())
        except ValueError:
            return {"ok": False, "error": "forbidden"}
    path = _path(target.home, target.slug)
    if not path.is_file():
        return {"ok": False, "error": "missing_status"}
    document = json.loads(path.read_text(encoding="utf-8"))
    return {"ok": True, "document": document}
