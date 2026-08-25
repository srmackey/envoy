from pathlib import Path

from tests.conftest import write_map, write_project

from envoy.status_store import status_get, status_put


def _seed(root: Path) -> None:
    write_map(
        root,
        [
            {"name": "nexus", "inbox": True, "description": "Nexus", "status": "active"},
            {"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"},
            {"name": "river", "inbox": True, "description": "River", "status": "active"},
        ],
    )
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
    write_project(
        root / "river",
        {
            "name": "river",
            "description": "River",
            "category": "tooling",
            "inbox": True,
            "status": "active",
            "services": ["mail"],
        },
    )


def test_status_put_requires_subscription(root: Path, home: Path) -> None:
    _seed(root)
    got = status_put(
        root, home, chair="river",
        forefront="X", where_i_left_off=["a"], next_steps=[], open_loops=[],
    )
    assert got == {"ok": False, "error": "not_subscribed"}


def test_status_put_overwrites_and_versions(root: Path, home: Path) -> None:
    _seed(root)
    first = status_put(
        root, home, chair="harbor",
        forefront="X", where_i_left_off=["did X"], next_steps=["1"], open_loops=[],
        repo="main · clean",
    )
    assert first["ok"] is True
    assert first["document"]["version"] == 1
    assert first["document"]["author"] == "harbor"
    assert first["document"]["repo"] == "main · clean"
    second = status_put(
        root, home, chair="harbor",
        forefront="Z", where_i_left_off=["X done", "now Z"], next_steps=[], open_loops=[],
    )
    assert second["document"]["version"] == 2
    assert second["document"]["forefront"] == "Z"
    assert "repo" not in second["document"] or second["document"].get("repo") in (None, "")
    got = status_get(root, home, chair="harbor")
    assert got["document"]["forefront"] == "Z"
    assert got["document"]["version"] == 2


def test_status_get_node_cannot_read_sibling(root: Path, home: Path) -> None:
    _seed(root)
    status_put(
        root, home, chair="harbor",
        forefront="X", where_i_left_off=["a"], next_steps=[], open_loops=[],
    )
    write_project(
        root / "river",
        {
            "name": "river",
            "description": "River",
            "category": "tooling",
            "inbox": True,
            "status": "active",
            "services": ["status"],
        },
    )
    got = status_get(root, home, chair="river", node="harbor")
    assert got == {"ok": False, "error": "forbidden"}


def test_status_get_nexus_reads_child(root: Path, home: Path) -> None:
    _seed(root)
    status_put(
        root, home, chair="harbor",
        forefront="X", where_i_left_off=["a"], next_steps=["n"], open_loops=["o"],
    )
    got = status_get(root, home, chair="nexus", node="harbor")
    assert got["ok"] is True
    assert got["document"]["forefront"] == "X"
    assert got["document"]["next_steps"] == ["n"]
