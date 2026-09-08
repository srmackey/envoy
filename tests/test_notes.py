from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.conftest import write_map, write_project

from envoy.notes_store import note_ack, note_gate, note_list, note_post, note_remove


def _seed(root: Path) -> None:
    write_map(
        root,
        [
            {"name": "nexus", "inbox": True, "description": "Nexus", "status": "active"},
            {"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"},
            {"name": "river", "inbox": True, "description": "River", "status": "active"},
        ],
    )
    for name in ("harbor", "river"):
        write_project(
            root / name,
            {
                "name": name,
                "description": name.title(),
                "category": "tooling",
                "inbox": True,
                "status": "active",
                "services": ["mail"],
            },
        )
    write_project(
        root,
        {
            "name": "nexus",
            "description": "Nexus",
            "category": "nexus",
            "inbox": True,
            "status": "active",
            "services": ["status", "mail"],
        },
    )


def test_note_post_and_visibility(root: Path, home: Path) -> None:
    _seed(root)
    posted = note_post(
        root, home, chair="harbor",
        intended_for="nexus", inbox="inbox/letter.md", why="export for catalog",
    )
    assert posted["ok"] is True
    note_id = posted["note"]["id"]
    assert posted["note"]["author"] == "harbor"
    assert "gate" not in posted["note"]
    nexus_list = note_list(root, home, chair="nexus")
    assert nexus_list["notes"][0]["id"] == note_id
    river_list = note_list(root, home, chair="river")
    assert river_list["notes"] == []
    harbor_list = note_list(root, home, chair="harbor")
    assert len(harbor_list["notes"]) == 1
    assert "gate" not in harbor_list["notes"][0]


def test_intended_for_can_list_and_ack(root: Path, home: Path) -> None:
    _seed(root)
    posted = note_post(
        root, home, chair="nexus",
        intended_for="harbor", inbox="harbor/inbox/letter.md", why="deliver catalog",
    )
    assert posted["ok"] is True
    note_id = posted["note"]["id"]
    harbor_list = note_list(root, home, chair="harbor")
    assert len(harbor_list["notes"]) == 1
    assert harbor_list["notes"][0]["id"] == note_id
    assert "gate" not in harbor_list["notes"][0]
    river_list = note_list(root, home, chair="river")
    assert river_list["notes"] == []
    denied = note_ack(root, home, chair="river", note_id=note_id, action="shown")
    assert denied["error"] == "forbidden"
    acked = note_ack(root, home, chair="harbor", note_id=note_id, action="shown")
    assert acked["ok"] is True
    assert acked["note"]["ack"]["chair"] == "harbor"
    assert acked["note"]["ack"]["action"] == "shown"


def test_note_gate_nexus_only_and_stripped(root: Path, home: Path) -> None:
    _seed(root)
    posted = note_post(
        root, home, chair="harbor",
        intended_for="unknown-place", inbox="inbox/x.md", why="guess",
    )
    note_id = posted["note"]["id"]
    denied = note_gate(root, home, chair="harbor", note_id=note_id, gate="foul")
    assert denied["error"] == "nexus_only"
    gated = note_gate(root, home, chair="nexus", note_id=note_id, gate="foul", gate_note="not a map name")
    assert gated["ok"] is True
    nexus_list = note_list(root, home, chair="nexus")
    assert nexus_list["notes"][0]["gate"] == "foul"
    harbor_list = note_list(root, home, chair="harbor")
    assert "gate" not in harbor_list["notes"][0]


def test_note_remove_author_only(root: Path, home: Path) -> None:
    _seed(root)
    posted = note_post(
        root, home, chair="harbor",
        intended_for="nexus", inbox="inbox/x.md", why="why",
    )
    note_id = posted["note"]["id"]
    denied = note_remove(root, home, chair="nexus", note_id=note_id)
    assert denied["error"] == "not_author"
    removed = note_remove(root, home, chair="harbor", note_id=note_id)
    assert removed["ok"] is True
    assert note_list(root, home, chair="nexus")["notes"] == []


def test_acked_notes_expire_after_14_days(root: Path, home: Path) -> None:
    _seed(root)
    posted = note_post(
        root, home, chair="harbor",
        intended_for="nexus", inbox="inbox/x.md", why="why",
    )
    note_id = posted["note"]["id"]
    note_ack(root, home, chair="nexus", note_id=note_id, action="delivered")
    future = datetime.now(timezone.utc) + timedelta(days=15)
    listed = note_list(root, home, chair="nexus", now=future)
    assert listed["notes"] == []
    hold = note_post(
        root, home, chair="harbor",
        intended_for="nexus", inbox="inbox/y.md", why="hold me",
    )
    hold_id = hold["note"]["id"]
    note_gate(root, home, chair="nexus", note_id=hold_id, gate="hold")
    note_ack(root, home, chair="nexus", note_id=hold_id, action="held")
    still = note_list(root, home, chair="nexus", now=future)
    assert len(still["notes"]) == 1
    assert still["notes"][0]["id"] == hold_id
