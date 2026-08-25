from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def chair_folder(root: Path, name: str) -> Path:
    if name == "nexus":
        return root
    return root / name


def load_project(root: Path, name: str) -> dict[str, Any] | None:
    path = chair_folder(root, name) / "project.yaml"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return None
    return data


def _read_map(root: Path) -> dict[str, Any] | None:
    path = root / "MAP.md"
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {"updated": "", "entries": []}
    entries = data.get("entries") or []
    if not isinstance(entries, list):
        entries = []
    return {"updated": str(data.get("updated") or ""), "entries": list(entries)}


def known_chairs(root: Path) -> set[str]:
    data = _read_map(root)
    names = {"nexus"}
    if data is None:
        return names
    for row in data["entries"]:
        if isinstance(row, dict) and row.get("name"):
            names.add(str(row["name"]))
    return names


def _unknown_chair(root: Path, chair: str, *, allow_nexus_bootstrap: bool = False) -> dict | None:
    if allow_nexus_bootstrap and chair == "nexus":
        return None
    if chair not in known_chairs(root):
        return {"ok": False, "error": "unknown_chair"}
    return None


def map_list(root: Path, chair: str) -> dict[str, Any]:
    data = _read_map(root)
    if data is None:
        return {"ok": False, "error": "missing_map"}
    err = _unknown_chair(root, chair)
    if err:
        return err
    entries: list[dict[str, Any]] = []
    for row in data["entries"]:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        if chair == "nexus":
            proj = load_project(root, str(item.get("name") or ""))
            if proj is not None:
                if "category" in proj:
                    item["category"] = proj["category"]
                if "services" in proj:
                    item["services"] = proj["services"]
        entries.append(item)
    return {"ok": True, "updated": data["updated"], "entries": entries}


def map_upsert(root: Path, chair: str, entry: dict[str, Any]) -> dict[str, Any]:
    if chair != "nexus":
        err = _unknown_chair(root, chair)
        if err:
            return err
        return {"ok": False, "error": "nexus_only"}
    required = ("name", "inbox", "description", "status")
    if any(k not in entry for k in required):
        return {"ok": False, "error": "invalid_payload"}
    data = _read_map(root) or {"updated": "", "entries": []}
    name = str(entry["name"])
    rows: list[dict[str, Any]] = []
    replaced = False
    for row in data["entries"]:
        if isinstance(row, dict) and str(row.get("name")) == name:
            rows.append({
                "name": name,
                "inbox": bool(entry["inbox"]),
                "description": str(entry["description"]),
                "status": str(entry["status"]),
            })
            replaced = True
        elif isinstance(row, dict):
            rows.append(row)
    if not replaced:
        rows.append({
            "name": name,
            "inbox": bool(entry["inbox"]),
            "description": str(entry["description"]),
            "status": str(entry["status"]),
        })
    today = datetime.now(timezone.utc).date().isoformat()
    payload = {"updated": today, "entries": rows}
    (root / "MAP.md").write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return {"ok": True, "updated": today, "entries": rows}
