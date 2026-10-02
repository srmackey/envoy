from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from envoy.address import Tree, load_tree, resolve

_STORE = "_envoy"


@dataclass(frozen=True)
class Chair:
    address: str
    slug: str
    home: Path
    project_dir: Path
    is_nexus: bool
    is_root: bool
    legacy: bool


def chair_folder(root: Path, name: str) -> Path:
    if name == "nexus":
        return root
    return root / name


def open_chair(root: Path, chair: str, default_home: Path) -> Chair | None:
    """The store and record for a chair.

    When nexus.md is at the bulletin root, the address selects that nexus's
    `_envoy/` store and the record name is the folder basename. `nexus` is
    the root nexus. A bare name that matches one node is that node's address.
    Without nexus.md, the single ENVOY_HOME and MAP.md names stay in force.
    """
    tree = load_tree(root)
    if tree is not None:
        located = resolve(tree, chair, root_alias=True)
        if located is None:
            return None
        return Chair(
            address=located.address,
            slug=located.slug,
            home=located.nexus_dir / _STORE,
            project_dir=located.project_dir,
            is_nexus=located.is_nexus,
            is_root=located.is_root,
            legacy=False,
        )
    if chair not in _map_names(root):
        return None
    return Chair(
        address=chair,
        slug=chair,
        home=default_home,
        project_dir=chair_folder(root, chair),
        is_nexus=chair == "nexus",
        is_root=chair == "nexus",
        legacy=True,
    )


def nexus_homes(root: Path) -> list[Path]:
    tree = load_tree(root)
    if tree is None:
        return []
    return [nexus.folder / _STORE for nexus in tree.nexuses.values()]


def load_project(root: Path, name: str) -> dict[str, Any] | None:
    tree = load_tree(root)
    if tree is not None:
        located = resolve(tree, name, root_alias=True)
        if located is None:
            return None
        path = located.project_dir / "project.yaml"
    else:
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
    tree = load_tree(root)
    if tree is not None:
        return _tree_names(tree)
    return _map_names(root)


def _map_names(root: Path) -> set[str]:
    data = _read_map(root)
    names = {"nexus"}
    if data is None:
        return names
    for row in data["entries"]:
        if isinstance(row, dict) and row.get("name"):
            names.add(str(row["name"]))
    return names


def _tree_names(tree: Tree) -> set[str]:
    names = {"nexus", tree.top.name.casefold()}
    bare: dict[str, int] = {}
    for nexus in tree.nexuses.values():
        names.add(nexus.name.casefold())
        for node in nexus.nodes:
            if node.kind == "nexus":
                continue
            names.add(f"{nexus.name.casefold()}/{node.name.casefold()}")
            bare[node.name.casefold()] = bare.get(node.name.casefold(), 0) + 1
    for name, count in bare.items():
        if count == 1:
            names.add(name)
    return names


def _unknown_chair(root: Path, chair: str, *, allow_nexus_bootstrap: bool = False) -> dict | None:
    if allow_nexus_bootstrap and chair == "nexus":
        return None
    if chair not in known_chairs(root):
        return {"ok": False, "error": "unknown_chair"}
    return None


def map_list(root: Path, chair: str) -> dict[str, Any]:
    tree = load_tree(root)
    if tree is not None:
        return _map_list_tree(root, tree, chair)
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
    tree = load_tree(root)
    if tree is not None:
        return _map_upsert_tree(root, chair, entry)
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


def _map_list_tree(root: Path, tree: Tree, chair: str) -> dict[str, Any]:
    caller = open_chair(root, chair, root)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    located = resolve(tree, caller.address)
    if located is None:
        return {"ok": False, "error": "unknown_chair"}
    nexus = tree.nexuses[located.address.split("/")[0]]
    if located.is_nexus:
        nexus = tree.nexuses[located.address]
    entries: list[dict[str, Any]] = []
    for node in nexus.nodes:
        if node.kind == "nexus":
            name = node.name.casefold()
        else:
            name = f"{nexus.name.casefold()}/{node.name.casefold()}"
        item: dict[str, Any] = {
            "name": name,
            "kind": node.kind,
            "inbox": "mail" in node.services,
            "description": node.triggers,
            "status": node.status,
        }
        if caller.is_nexus:
            proj = load_project(root, name)
            if proj is not None:
                if "category" in proj:
                    item["category"] = proj["category"]
                if "services" in proj:
                    item["services"] = proj["services"]
            elif node.services:
                item["services"] = list(node.services)
        entries.append(item)
    return {"ok": True, "updated": "", "entries": entries}


def _map_upsert_tree(root: Path, chair: str, entry: dict[str, Any]) -> dict[str, Any]:
    caller = open_chair(root, chair, root)
    if caller is None:
        return {"ok": False, "error": "unknown_chair"}
    if not caller.is_nexus:
        return {"ok": False, "error": "nexus_only"}
    required = ("name", "inbox", "description", "status")
    if any(k not in entry for k in required):
        return {"ok": False, "error": "invalid_payload"}
    raw_name = str(entry["name"]).strip().replace("\\", "/")
    parts = [part for part in raw_name.split("/") if part]
    if len(parts) > 2 or any(part in {".", ".."} for part in parts):
        return {"ok": False, "error": "invalid_payload"}
    if len(parts) == 2:
        if parts[0].casefold() != caller.address:
            return {"ok": False, "error": "not_in_nexus"}
        row_name = parts[1]
    else:
        row_name = parts[0] if parts else ""
    if not row_name:
        return {"ok": False, "error": "invalid_payload"}
    path = caller.project_dir / "nexus.md"
    if not path.is_file():
        return {"ok": False, "error": "missing_map"}
    _rewrite_node_row(
        path,
        row_name,
        status=str(entry["status"]),
        description=str(entry["description"]),
    )
    return _map_list_tree(root, load_tree(root), chair)  # type: ignore[arg-type]


def _rewrite_node_row(path: Path, row_name: str, *, status: str, description: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    header_at = None
    header: list[str] = []
    for index, line in enumerate(lines):
        cells = _table_cells(line)
        folded = [cell.casefold() for cell in cells]
        if cells and folded[0] == "node" and "path" in folded:
            header_at = index
            header = folded
            break
    if header_at is None:
        raise ValueError("nexus.md has no nodes table")
    status_at = header.index("status") if "status" in header else None
    triggers_at = header.index("triggers") if "triggers" in header else None
    replaced = False
    end = header_at + 1
    for index in range(header_at + 1, len(lines)):
        cells = _table_cells(lines[index])
        if not cells:
            break
        if all(cell and set(cell) <= set("-: ") for cell in cells):
            end = index + 1
            continue
        end = index + 1
        if cells[0].casefold() == row_name.casefold():
            if status_at is not None and status_at < len(cells):
                cells[status_at] = status
            if triggers_at is not None and triggers_at < len(cells):
                cells[triggers_at] = description
            lines[index] = _join_cells(cells)
            replaced = True
            break
    if not replaced:
        fresh = [""] * len(header)
        fresh[0] = row_name
        if "path" in header:
            fresh[header.index("path")] = f"{row_name}/"
        if "kind" in header:
            fresh[header.index("kind")] = "node"
        if status_at is not None:
            fresh[status_at] = status
        if "sensitive" in header:
            fresh[header.index("sensitive")] = "no"
        if "always-on" in header:
            fresh[header.index("always-on")] = "no"
        if triggers_at is not None:
            fresh[triggers_at] = description
        lines.insert(end, _join_cells(fresh))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _table_cells(line: str) -> list[str]:
    raw = line.strip()
    if not raw.startswith("|"):
        return []
    return [part.strip() for part in raw.strip("|").split("|")]


def _join_cells(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"
