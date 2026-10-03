from pathlib import Path

from tests.conftest import write_map, write_project

from envoy.now import now_view
from envoy.status_store import status_put


NOW = """# NOW
updated: 2026-08-25

## This week

1. **Chart the harbor** · due: none · node: harbor
2. **Lane 1 packs** · due: none · node: cove

## Later

- **Owner roots** · due: none · node: none
"""


def _seed(root: Path) -> None:
    write_map(
        root,
        [
            {"name": "nexus", "inbox": True, "description": "Nexus", "status": "active"},
            {"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"},
            {"name": "reef", "inbox": True, "description": "Reef node", "status": "active"},
            {"name": "cove", "inbox": True, "description": "Cove node", "status": "active"},
        ],
    )
    (root / "always-on.yaml").write_text(
        "always_on:\n  - reef\n  - cove\n",
        encoding="utf-8",
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
    (root / "FOCUS.md").write_text(NOW, encoding="utf-8")


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
    assert by_text["Lane 1 packs"]["state"] == "no_trail"
    assert by_text["Lane 1 packs"]["forefront"] is None
    fronts = {row["node"]: row for row in got["forefronts"]}
    assert "next_steps" not in fronts["harbor"]
    assert fronts["harbor"]["forefront"] == "Moor the river"
    assert "reef" in got["always_on_missing"]
    assert "cove" not in got["always_on_missing"]


def test_now_view_always_on_empty_when_file_missing(root: Path, home: Path) -> None:
    write_map(
        root,
        [
            {"name": "nexus", "inbox": True, "description": "Nexus", "status": "active"},
            {"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"},
        ],
    )
    (root / "FOCUS.md").write_text(
        "# FOCUS\nupdated: 2026-08-25\n\n## This week\n\n1. **Chart the harbor** · due: none · node: harbor\n",
        encoding="utf-8",
    )
    got = now_view(root, home, chair="nexus")
    assert got["always_on_missing"] == []


def test_now_view_no_trail_when_no_sitrep(root: Path, home: Path) -> None:
    _seed(root)
    got = now_view(root, home, chair="nexus")
    row = next(r for r in got["reconcile"] if r["text"] == "Lane 1 packs")
    assert row["state"] == "no_trail"
    assert row["forefront"] is None


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


def test_now_view_reads_legacy_file_when_focus_is_absent(root: Path, home: Path) -> None:
    _seed(root)
    (root / "FOCUS.md").unlink()
    (root / "NOW.md").write_text(NOW, encoding="utf-8")
    got = now_view(root, home, chair="harbor")
    assert got["ok"] is True
    assert got["now"]["this_week"][0]["text"] == "Chart the harbor"


def test_node_reads_its_nexus_board(tmp_path: Path, home: Path) -> None:
    root = tmp_path / "coast"
    root.mkdir()
    (root / "nexus.md").write_text(
        "\n".join([
            "# nexus: coast",
            "focus: harbor",
            "",
            "| Node | Path | Kind | Status | Sensitive | Always-on | Services | Triggers |",
            "|---|---|---|---|---|---|---|---|",
            "| harbor | harbor/ | nexus | active | no | no | status, mail | inner |",
            "| ledger | ledger/ | node | active | no | yes | status | tide book |",
        ]) + "\n",
        encoding="utf-8",
    )
    harbor = root / "harbor"
    harbor.mkdir()
    (harbor / "nexus.md").write_text(
        "\n".join([
            "# nexus: harbor",
            "parent: coast",
            "",
            "| Node | Path | Kind | Status | Sensitive | Always-on | Services | Triggers |",
            "|---|---|---|---|---|---|---|---|",
            "| dock | dock/ | node | active | no | yes | status, mail | the dock |",
            "| skiff | skiff/ | node | active | no | yes | status | the skiff |",
        ]) + "\n",
        encoding="utf-8",
    )
    (harbor / "dock").mkdir()
    for folder in (root / "ledger", harbor / "dock"):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "project.yaml").write_text(
            "services:\n- status\n- mail\n",
            encoding="utf-8",
        )
    (root / "FOCUS.md").write_text(
        "# FOCUS\nupdated: 2026-10-03\n\n## This week\n\n1. **Mind the ledger** · due: none · node: ledger\n",
        encoding="utf-8",
    )
    (harbor / "FOCUS.md").write_text(
        "# FOCUS\nupdated: 2026-10-03\n\n## This week\n\n1. **Paint the dock** · due: none · node: dock\n",
        encoding="utf-8",
    )
    status_put(
        root, home, chair="harbor/dock",
        forefront="Paint the dock",
        where_i_left_off=["still painting"],
        next_steps=[],
        open_loops=[],
    )
    status_put(
        root, home, chair="ledger",
        forefront="Count the tide",
        where_i_left_off=["counted"],
        next_steps=[],
        open_loops=[],
    )
    node = now_view(root, home, chair="harbor/dock")
    assert node["ok"] is True
    assert "reconcile" not in node
    assert node["now"]["this_week"][0]["text"] == "Paint the dock"
    parent = now_view(root, home, chair="coast")
    assert parent["focus"]["node"] == "harbor"
    assert parent["focus"]["this_week"][0]["text"] == "Paint the dock"
    assert parent["now"]["this_week"][0]["text"] == "Mind the ledger"
    names = {row["node"] for row in parent["forefronts"]}
    assert "harbor/dock" not in names
    assert any(name and name.endswith("ledger") for name in names)
    missing = {item.casefold() for item in parent["always_on_missing"]}
    assert missing == {"skiff"}
