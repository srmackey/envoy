"""The agenda: one store on the root nexus, edits refused for the wrong chair."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml
from tests.conftest import write_map, write_project

from envoy.agenda_store import (
    agenda_close,
    agenda_list,
    agenda_post,
    agenda_reorder,
    agenda_update,
)

# A Wednesday. Tomorrow is Thursday, this Sunday is 2026-12-06, next week runs 12-07 to 12-13.
WED = date(2026, 12, 2)


def _nexus(folder: Path, name: str, rows: list[str], parent: str | None = None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    lines = [f"# nexus: {name}", ""]
    if parent:
        lines.extend([f"parent: {parent}", ""])
    lines.extend(
        [
            "| Node | Path | Kind | Status | Sensitive | Services | Triggers |",
            "|---|---|---|---|---|---|---|",
            *rows,
        ]
    )
    (folder / "nexus.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _project(folder: Path, services: list[str]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "project.yaml").write_text(
        yaml.safe_dump({"services": services}, sort_keys=False), encoding="utf-8"
    )


@pytest.fixture
def coast(tmp_path: Path) -> Path:
    """coast (root) holds harbor (a nexus) and ledger. harbor holds dock and buoy."""
    root = tmp_path / "coast"
    _nexus(
        root,
        "coast",
        [
            "| harbor | harbor/ | nexus | active | no | status, mail, agenda | the harbor |",
            "| ledger | ledger/ | node | active | no | status, agenda | the tide ledger |",
        ],
    )
    _nexus(
        root / "harbor",
        "harbor",
        [
            "| dock | dock/ | node | active | no | agenda | the dock |",
            "| buoy | buoy/ | node | active | no | status | the buoy |",
        ],
        parent="coast",
    )
    _project(root, ["status", "mail", "agenda"])
    _project(root / "harbor", ["status", "mail", "agenda"])
    _project(root / "ledger", ["status", "agenda"])
    _project(root / "harbor" / "dock", ["agenda"])
    _project(root / "harbor" / "buoy", ["status"])
    return root


def test_post_from_any_depth_lands_in_root_store(coast: Path, home: Path) -> None:
    deep = agenda_post(coast, home, "harbor/dock", "Paint the hull")
    assert deep["ok"] is True
    assert deep["item"]["author"] == "harbor/dock"
    item_id = deep["item"]["id"]
    assert (coast / "_envoy" / "agenda" / f"{item_id}.json").is_file()
    assert not (coast / "harbor" / "_envoy" / "agenda").exists()
    assert not (home / "agenda").exists()


def test_post_requires_agenda_service(coast: Path, home: Path) -> None:
    refused = agenda_post(coast, home, "harbor/buoy", "Ring at noon")
    assert refused == {"ok": False, "error": "not_subscribed"}
    assert agenda_post(coast, home, "nowhere", "x")["error"] == "unknown_chair"


def test_post_checks_dates(coast: Path, home: Path) -> None:
    assert agenda_post(coast, home, "ledger", "")["error"] == "invalid_payload"
    assert agenda_post(coast, home, "ledger", "x", due="12/02/2026")["error"] == "invalid_date"
    assert agenda_post(coast, home, "ledger", "x", due="2026-02-30")["error"] == "invalid_date"
    assert agenda_post(coast, home, "ledger", "x", until="2026-12-02")["error"] == "invalid_window"
    backwards = agenda_post(coast, home, "ledger", "x", due="2026-12-05", until="2026-12-04")
    assert backwards["error"] == "invalid_window"


def test_chair_edits_only_its_own_rows(coast: Path, home: Path) -> None:
    mine = agenda_post(coast, home, "ledger", "Count the tides")["item"]["id"]
    theirs = agenda_post(coast, home, "harbor/dock", "Paint the hull")["item"]["id"]

    assert agenda_update(coast, home, "ledger", theirs, text="mine now")["error"] == "not_author"
    assert agenda_close(coast, home, "ledger", theirs)["error"] == "not_author"
    assert agenda_update(coast, home, "harbor", theirs, text="parent nexus")["error"] == "not_author"

    changed = agenda_update(coast, home, "ledger", mine, text="Count the spring tides")
    assert changed["ok"] is True
    assert changed["item"]["text"] == "Count the spring tides"
    assert agenda_close(coast, home, "ledger", mine)["ok"] is True


def test_root_edits_and_closes_any_row(coast: Path, home: Path) -> None:
    theirs = agenda_post(coast, home, "harbor/dock", "Paint the hull")["item"]["id"]
    edited = agenda_update(coast, home, "coast", theirs, text="Paint the hull blue")
    assert edited["ok"] is True
    assert edited["item"]["author"] == "harbor/dock"
    closed = agenda_close(coast, home, "nexus", theirs)
    assert closed["ok"] is True
    assert closed["item"]["closed"]["chair"] == "coast"
    assert agenda_update(coast, home, "coast", theirs, text="again")["error"] == "closed"


def test_unknown_item(coast: Path, home: Path) -> None:
    assert agenda_close(coast, home, "ledger", "0" * 32)["error"] == "missing_item"
    assert agenda_close(coast, home, "ledger", "../escape")["error"] == "missing_item"


def test_new_task_lands_at_bottom_and_only_root_reorders(coast: Path, home: Path) -> None:
    a = agenda_post(coast, home, "ledger", "First")["item"]["id"]
    b = agenda_post(coast, home, "harbor/dock", "Second")["item"]["id"]
    c = agenda_post(coast, home, "ledger", "Third")["item"]["id"]
    listed = agenda_list(coast, home, "ledger", today=WED)
    assert [t["id"] for t in listed["tasks"]] == [a, b, c]

    assert agenda_reorder(coast, home, "harbor", [c])["error"] == "root_only"
    assert agenda_reorder(coast, home, "ledger", [c])["error"] == "root_only"

    moved = agenda_reorder(coast, home, "coast", [c])
    assert moved["ok"] is True
    assert [t["id"] for t in moved["tasks"]] == [c, a, b]

    d = agenda_post(coast, home, "ledger", "Fourth")["item"]["id"]
    listed = agenda_list(coast, home, "harbor/dock", today=WED)
    assert [t["id"] for t in listed["tasks"]] == [c, a, b, d]


def test_reorder_refuses_dated_or_unknown_ids(coast: Path, home: Path) -> None:
    task = agenda_post(coast, home, "ledger", "Task")["item"]["id"]
    dated = agenda_post(coast, home, "ledger", "Dated", due="2026-12-03")["item"]["id"]
    refused = agenda_reorder(coast, home, "coast", [dated, task])
    assert refused["error"] == "not_a_task"
    assert refused["items"] == [dated]
    assert agenda_reorder(coast, home, "coast", [task, task])["error"] == "invalid_payload"
    assert agenda_reorder(coast, home, "coast", [])["error"] == "invalid_payload"


def test_giving_a_task_a_date_moves_it_to_the_calendar(coast: Path, home: Path) -> None:
    a = agenda_post(coast, home, "ledger", "First")["item"]["id"]
    b = agenda_post(coast, home, "ledger", "Second")["item"]["id"]
    dated = agenda_update(coast, home, "ledger", a, due="2026-12-03")
    assert dated["item"]["rank"] is None
    listed = agenda_list(coast, home, "ledger", today=WED)
    assert [t["id"] for t in listed["tasks"]] == [b]
    assert [r["id"] for r in listed["calendar"]["due_soon"]] == [a]

    back = agenda_update(coast, home, "ledger", a, due="")
    assert back["item"]["due"] is None
    listed = agenda_list(coast, home, "ledger", today=WED)
    assert [t["id"] for t in listed["tasks"]] == [b, a]


def test_window_update_and_clear(coast: Path, home: Path) -> None:
    row = agenda_post(coast, home, "ledger", "Survey", due="2026-12-08")["item"]["id"]
    widened = agenda_update(coast, home, "ledger", row, until="2026-12-10")
    assert widened["item"]["until"] == "2026-12-10"
    assert agenda_update(coast, home, "ledger", row, until="2026-12-01")["error"] == "invalid_window"
    narrowed = agenda_update(coast, home, "ledger", row, until="")
    assert narrowed["item"]["until"] is None
    assert narrowed["item"]["due"] == "2026-12-08"


def test_buckets_count_each_item_once_in_its_earliest_bucket(coast: Path, home: Path) -> None:
    def post(text: str, due: str, until: str | None = None) -> str:
        return agenda_post(coast, home, "ledger", text, due=due, until=until)["item"]["id"]

    overdue = post("Overdue", "2026-11-30")
    span_over = post("Window that ended", "2026-11-25", "2026-12-01")
    span_live = post("Window running through today", "2026-11-28", "2026-12-04")
    today = post("Today", "2026-12-02")
    tomorrow = post("Tomorrow", "2026-12-03")
    friday = post("Friday", "2026-12-04")
    sunday = post("Sunday", "2026-12-06")
    span_next = post("Saturday into next week", "2026-12-05", "2026-12-09")
    monday = post("Next Monday", "2026-12-07")
    next_sunday = post("Next Sunday", "2026-12-13")
    later = post("Later", "2026-12-14")
    agenda_post(coast, home, "ledger", "A task")

    listed = agenda_list(coast, home, "harbor/dock", today=WED)
    ids = {name: [r["id"] for r in rows] for name, rows in listed["calendar"].items()}
    assert ids["overdue"] == [span_over, overdue]
    assert ids["due_soon"] == [span_live, today, tomorrow]
    assert ids["before_sunday"] == [friday, span_next, sunday]
    assert ids["next_week"] == [monday, next_sunday]
    assert ids["later"] == [later]
    assert listed["counts"] == {
        "overdue": 2,
        "due_soon": 3,
        "before_sunday": 3,
        "next_week": 2,
        "later": 1,
        "tasks": 1,
    }
    assert listed["next"]["id"] == span_over


def test_next_is_soonest_when_nothing_overdue(coast: Path, home: Path) -> None:
    agenda_post(coast, home, "ledger", "Next week", due="2026-12-08")
    soon = agenda_post(coast, home, "ledger", "Friday", due="2026-12-04")["item"]["id"]
    assert agenda_list(coast, home, "ledger", today=WED)["next"]["id"] == soon
    agenda_close(coast, home, "ledger", soon)
    assert agenda_list(coast, home, "ledger", today=WED)["next"]["text"] == "Next week"


def test_sunday_edges(coast: Path, home: Path) -> None:
    agenda_post(coast, home, "ledger", "Today", due="2026-12-06")
    agenda_post(coast, home, "ledger", "Monday", due="2026-12-07")
    agenda_post(coast, home, "ledger", "Tuesday", due="2026-12-08")
    agenda_post(coast, home, "ledger", "Following Sunday", due="2026-12-13")
    agenda_post(coast, home, "ledger", "Monday after", due="2026-12-14")
    on_sunday = agenda_list(coast, home, "ledger", today=date(2026, 12, 6))["counts"]
    assert on_sunday["due_soon"] == 2
    assert on_sunday["before_sunday"] == 0
    assert on_sunday["next_week"] == 2
    assert on_sunday["later"] == 1

    on_saturday = agenda_list(coast, home, "ledger", today=date(2026, 12, 5))["counts"]
    assert on_saturday["due_soon"] == 1
    assert on_saturday["before_sunday"] == 0
    assert on_saturday["next_week"] == 3


def test_reading_never_closes_a_row(coast: Path, home: Path) -> None:
    row = agenda_post(coast, home, "harbor/dock", "Paint", due="2026-11-01")["item"]["id"]
    for chair in ("harbor/dock", "coast", "ledger"):
        agenda_list(coast, home, chair, today=WED)
        agenda_list(coast, home, chair, "mine", today=WED)
    listed = agenda_list(coast, home, "coast", today=WED)
    assert [r["id"] for r in listed["calendar"]["overdue"]] == [row]
    assert listed["calendar"]["overdue"][0]["closed"] is None


def test_mine_is_only_rows_this_chair_posted(coast: Path, home: Path) -> None:
    agenda_post(coast, home, "ledger", "Ledger task")
    agenda_post(coast, home, "harbor/dock", "Dock date", due="2026-12-03")
    agenda_post(coast, home, "coast", "Root task")

    dock = agenda_list(coast, home, "harbor/dock", "mine", today=WED)
    assert dock["counts"]["tasks"] == 0
    assert [r["text"] for r in dock["calendar"]["due_soon"]] == ["Dock date"]

    root = agenda_list(coast, home, "coast", "mine", today=WED)
    assert [t["text"] for t in root["tasks"]] == ["Root task"]
    assert root["counts"]["due_soon"] == 0

    everything = agenda_list(coast, home, "harbor/buoy", today=WED)
    assert everything["counts"]["tasks"] == 2
    assert everything["counts"]["due_soon"] == 1

    assert agenda_list(coast, home, "ledger", "theirs")["error"] == "invalid_payload"


def test_legacy_map_keeps_agenda_in_vault(root: Path, home: Path) -> None:
    write_map(
        root,
        [
            {"name": "nexus", "inbox": True, "description": "Nexus", "status": "active"},
            {"name": "mill", "inbox": True, "description": "Mill", "status": "active"},
            {"name": "weir", "inbox": True, "description": "Weir", "status": "active"},
        ],
    )
    write_project(root, {"name": "nexus", "services": ["agenda"]})
    write_project(root / "mill", {"name": "mill", "services": ["agenda"]})
    write_project(root / "weir", {"name": "weir", "services": ["agenda"]})

    row = agenda_post(root, home, "mill", "Grind")["item"]["id"]
    assert (home / "agenda" / f"{row}.json").is_file()
    assert agenda_close(root, home, "weir", row)["error"] == "not_author"
    assert agenda_reorder(root, home, "mill", [row])["error"] == "root_only"
    assert agenda_reorder(root, home, "nexus", [row])["ok"] is True
    assert agenda_close(root, home, "nexus", row)["ok"] is True
