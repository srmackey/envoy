from pathlib import Path

from tests.conftest import write_map, write_project

from envoy.now import now_view
from envoy.status_store import status_put


NOW = """# NOW
updated: 2026-08-25

## This week

1. **Chart the harbor** · due: none · node: harbor
2. **Lane 1 packs** · due: none · node: career

## Later

- **Owner roots** · due: none · node: none
"""


def _seed(root: Path) -> None:
    write_map(
        root,
        [
            {"name": "nexus", "inbox": True, "description": "Nexus", "status": "active"},
            {"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"},
            {"name": "family", "inbox": True, "description": "Family node", "status": "active"},
            {"name": "career", "inbox": True, "description": "Career node", "status": "active"},
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
    (root / "NOW.md").write_text(NOW, encoding="utf-8")


def test_now_view_node_gets_only_durable(root: Path, home: Path) -> None:
    _seed(root)
    got = now_view(root, home, chair="harbor")
    assert got["ok"] is True
    assert "reconcile" not in got
    assert got["now"]["this_week"][0]["text"] == "Chart the harbor"
    assert got["now"]["this_week"][0]["node"] == "harbor"
    assert got["now"]["later"][0]["node"] is None


def test_now_view_accounted_and_unaccounted(root: Path, home: Path) -> None:
    _seed(root)
    status_put(
        root, home, chair="harbor",
        forefront="Moor the river",
        where_i_left_off=["Chart the harbor done last sitting"],
        next_steps=["do not print"],
        open_loops=["do not print"],
    )
    got = now_view(root, home, chair="nexus")
    by_text = {row["text"]: row for row in got["reconcile"]}
    assert by_text["Chart the harbor"]["state"] == "accounted"
    assert by_text["Chart the harbor"]["forefront"] == "Moor the river"
    assert by_text["Lane 1 packs"]["state"] == "unaccounted"
    assert by_text["Lane 1 packs"]["forefront"] is None
    fronts = {row["node"]: row for row in got["forefronts"]}
    assert "next_steps" not in fronts["harbor"]
    assert fronts["harbor"]["forefront"] == "Moor the river"
    assert "family" in got["always_on_missing"]
    assert "career" not in got["always_on_missing"]


def test_now_view_unaccounted_when_trail_silent(root: Path, home: Path) -> None:
    _seed(root)
    status_put(
        root, home, chair="harbor",
        forefront="Moor the river",
        where_i_left_off=["worked on docks"],
        next_steps=[],
        open_loops=[],
    )
    got = now_view(root, home, chair="nexus")
    row = next(r for r in got["reconcile"] if r["text"] == "Chart the harbor")
    assert row["state"] == "unaccounted"


def test_now_view_current_when_forefront_matches(root: Path, home: Path) -> None:
    _seed(root)
    status_put(
        root, home, chair="harbor",
        forefront="Chart the harbor",
        where_i_left_off=["still on it"],
        next_steps=[],
        open_loops=[],
    )
    got = now_view(root, home, chair="nexus")
    row = next(r for r in got["reconcile"] if r["text"] == "Chart the harbor")
    assert row["state"] == "current"


def test_now_view_satisfied_when_board_text_in_repo(root: Path, home: Path) -> None:
    _seed(root)
    status_put(
        root, home, chair="harbor",
        forefront="Moor the river",
        where_i_left_off=["worked on docks"],
        next_steps=[],
        open_loops=[],
        repo="main · clean · Chart the harbor pushed",
    )
    got = now_view(root, home, chair="nexus")
    row = next(r for r in got["reconcile"] if r["text"] == "Chart the harbor")
    assert row["state"] == "satisfied"
    assert row["forefront"] == "Moor the river"
