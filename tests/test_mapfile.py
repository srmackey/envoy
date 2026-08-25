from pathlib import Path

from tests.conftest import write_map, write_project

from envoy.mapfile import map_list, map_upsert


def test_map_list_missing_file(root: Path) -> None:
    got = map_list(root, chair="nexus")
    assert got == {"ok": False, "error": "missing_map"}


def test_map_list_node_has_no_join(root: Path) -> None:
    write_map(root, [{"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"}])
    write_project(
        root / "harbor",
        {
            "name": "harbor",
            "description": "Harbor",
            "category": "tooling",
            "inbox": True,
            "status": "active",
            "services": ["status", "mail"],
        },
    )
    got = map_list(root, chair="harbor")
    assert got["ok"] is True
    assert "category" not in got["entries"][0]


def test_map_list_nexus_joins_project_yaml(root: Path) -> None:
    write_map(root, [{"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"}])
    write_project(
        root / "harbor",
        {
            "name": "harbor",
            "description": "Harbor",
            "category": "tooling",
            "inbox": True,
            "status": "active",
            "services": ["status"],
        },
    )
    got = map_list(root, chair="nexus")
    row = got["entries"][0]
    assert row["category"] == "tooling"
    assert row["services"] == ["status"]


def test_map_upsert_requires_nexus(root: Path) -> None:
    write_map(root, [{"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"}])
    got = map_upsert(
        root,
        chair="harbor",
        entry={"name": "river", "inbox": False, "description": "River", "status": "active"},
    )
    assert got["ok"] is False
    assert got["error"] == "nexus_only"


def test_map_upsert_creates_and_replaces(root: Path) -> None:
    first = map_upsert(
        root,
        chair="nexus",
        entry={"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"},
    )
    assert first["ok"] is True
    second = map_upsert(
        root,
        chair="nexus",
        entry={"name": "harbor", "inbox": False, "description": "Harbor shop", "status": "parked"},
    )
    listed = map_list(root, chair="nexus")
    assert len(listed["entries"]) == 1
    assert listed["entries"][0]["inbox"] is False
    assert listed["entries"][0]["description"] == "Harbor shop"
    assert listed["entries"][0]["status"] == "parked"
    assert second["ok"] is True
