from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.conftest import write_map, write_project

from envoy.now import now_view
from envoy.notes_store import note_post
from envoy.syos_store import syos_ack, syos_list, syos_post, syos_remove


def _seed(root: Path, *, harbor_services: list[str] | None = None) -> None:
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
            "services": harbor_services or ["syos"],
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


def test_syos_post_and_self_visibility(root: Path, home: Path) -> None:
    _seed(root)
    posted = syos_post(root, home, chair="harbor", body="PROTOCOL header is 2026-09-05")
    assert posted["ok"] is True
    note = posted["note"]
    assert note["kind"] == "syos"
    assert note["author"] == "harbor"
    assert note["intended_for"] == "harbor"
    assert note["body"] == "PROTOCOL header is 2026-09-05"
    assert note["ack"] is None
    assert "gate" not in note
    assert "inbox" not in note
    listed = syos_list(root, home, chair="harbor")
    assert len(listed["notes"]) == 1
    assert listed["notes"][0]["id"] == note["id"]


def test_syos_is_invisible_to_other_chairs_including_nexus(root: Path, home: Path) -> None:
    _seed(root)
    posted = syos_post(root, home, chair="harbor", body="check the skill copy")
    note_id = posted["note"]["id"]
    assert syos_list(root, home, chair="river")["notes"] == []
    nexus_notes = syos_list(root, home, chair="nexus")["notes"]
    assert all(item["id"] != note_id for item in nexus_notes)


def test_syos_post_requires_subscription(root: Path, home: Path) -> None:
    _seed(root)
    denied = syos_post(root, home, chair="river", body="nope")
    assert denied["ok"] is False
    assert denied["error"] == "not_subscribed"


def test_syos_post_unknown_chair(root: Path, home: Path) -> None:
    _seed(root)
    denied = syos_post(root, home, chair="unknown", body="nope")
    assert denied["error"] == "unknown_chair"


def test_syos_post_rejects_empty_body(root: Path, home: Path) -> None:
    _seed(root)
    denied = syos_post(root, home, chair="harbor", body="   ")
    assert denied["error"] == "invalid_payload"


def test_syos_remove_author_only(root: Path, home: Path) -> None:
    _seed(root)
    posted = syos_post(root, home, chair="harbor", body="brief")
    note_id = posted["note"]["id"]
    denied = syos_remove(root, home, chair="nexus", note_id=note_id)
    assert denied["error"] == "not_author"
    removed = syos_remove(root, home, chair="harbor", note_id=note_id)
    assert removed["ok"] is True
    assert syos_list(root, home, chair="harbor")["notes"] == []


def test_syos_acked_notes_expire_after_14_days(root: Path, home: Path) -> None:
    _seed(root)
    posted = syos_post(root, home, chair="harbor", body="brief")
    note_id = posted["note"]["id"]
    syos_ack(root, home, chair="harbor", note_id=note_id, action="shown")
    future = datetime.now(timezone.utc) + timedelta(days=15)
    listed = syos_list(root, home, chair="harbor", now=future)
    assert listed["notes"] == []
    kept = syos_post(root, home, chair="harbor", body="still open")
    still = syos_list(root, home, chair="harbor", now=future)
    assert len(still["notes"]) == 1
    assert still["notes"][0]["id"] == kept["note"]["id"]


def test_now_view_mail_does_not_include_syos(root: Path, home: Path) -> None:
    _seed(root, harbor_services=["status", "mail", "syos"])
    (root / "NOW.md").write_text(
        "# NOW\nupdated: 2026-09-05\n\n## This week\n\n## Later\n",
        encoding="utf-8",
    )
    mail = note_post(
        root, home, chair="harbor",
        intended_for="nexus", inbox="inbox/letter.md", why="export",
    )
    syos = syos_post(root, home, chair="harbor", body="other side brief")
    got = now_view(root, home, chair="nexus")
    mail_ids = {item["id"] for item in got["mail"]}
    assert mail["note"]["id"] in mail_ids
    assert syos["note"]["id"] not in mail_ids
    assert "syos" not in got
