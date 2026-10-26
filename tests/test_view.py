"""The local page reads the bulletin and does not mark mail seen."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from tests.conftest import write_map, write_project

from envoy.notes_store import note_post
from envoy.status_store import status_put
from envoy.view import node_detail, snapshot
from envoy.view_server import keep_page_up, make_server


def _coast(tmp_path: Path, *, harbor_sensitive: bool = False) -> Path:
    root = tmp_path / "coast"
    root.mkdir()
    (root / "nexus.md").write_text(
        "\n".join([
            "# nexus: coast",
            "focus: harbor",
            "",
            "| Node | Path | Kind | Status | Sensitive | Always-on | Services | Triggers |",
            "|---|---|---|---|---|---|---|---|",
            f"| harbor | harbor/ | nexus | active | {'yes' if harbor_sensitive else 'no'} | no | status, mail | inner |",
            "| ledger | ledger/ | node | active | no | no | status, mail | tide book |",
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
            "| dock | dock/ | node | active | no | no | status, mail | the dock |",
        ]) + "\n",
        encoding="utf-8",
    )
    (harbor / "dock").mkdir()
    (root / "ledger").mkdir()
    for folder in (root, root / "ledger", harbor / "dock"):
        (folder / "project.yaml").write_text(
            "services:\n- status\n- mail\n",
            encoding="utf-8",
        )
    (root / "FOCUS.md").write_text(
        "# FOCUS\nupdated: 2026-10-03\n\n## This week\n\n1. **Mind the ledger** · due: 2026-10-04 · node: ledger\n",
        encoding="utf-8",
    )
    (harbor / "FOCUS.md").write_text(
        "# FOCUS\nupdated: 2026-10-03\n\n## This week\n\n1. **Paint the dock** · due: none · node: dock\n",
        encoding="utf-8",
    )
    return root


def _local(folder: Path, forefront: str, *, loops: list[str] | None = None) -> None:
    status = folder / "_status"
    status.mkdir(parents=True, exist_ok=True)
    (status / "STATUS.md").write_text(
        "\n".join([
            "# STATUS",
            "updated: 2026-10-05",
            "repo: main · clean",
            "",
            "## Forefront",
            forefront,
            "",
            "## Where I left off",
            "- counted yesterday",
            "",
            "## Next steps",
            "1. count again",
            "",
            "## Open loops",
            *[f"- {loop}" for loop in loops or []],
            "",
        ]) + "\n",
        encoding="utf-8",
    )


def _addresses(entries: list[dict]) -> list[str]:
    found: list[str] = []
    for entry in entries:
        found.append(entry["address"])
        found.extend(_addresses(entry.get("children") or []))
    return found


def _health(snap: dict, address: str) -> dict:
    def find(entries: list[dict]) -> dict | None:
        for entry in entries:
            if entry["address"] == address:
                return entry
            hit = find(entry.get("children") or [])
            if hit:
                return hit
        return None

    entry = find(snap["tree"])
    assert entry is not None, address
    return entry["health"]


def test_snapshot_reads_tree_board_and_next_move(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    status_put(root, home, "ledger", "Count the tide", ["counted"], [], [])
    snap = snapshot(root, home, "coast", today=date(2026, 10, 3))
    assert snap["ok"] is True
    assert snap["chair"] == "coast"
    assert snap["view"] == "coast"
    assert _addresses(snap["tree"]) == ["coast", "harbor", "harbor/dock", "coast/ledger"]
    assert snap["tree"][0]["children"][0]["kind"] == "nexus"
    first, second = snap["board"]["sections"]
    assert first["name"] == "harbor"
    assert first["this_week"][0]["text"] == "Paint the dock"
    assert second["name"] == "coast"
    ledger = second["this_week"][0]
    assert ledger["address"] == "coast/ledger"
    assert ledger["days"] == 1
    assert ledger["state"] == "unaccounted"
    assert snap["next"]["text"] == "Paint the dock"
    assert snap["next"]["board"] == "harbor"
    # Due tomorrow is state on the line, not a signal.
    assert snap["attention"][0]["kinds"] == ["unaccounted"]
    assert snap["attention"][0]["address"] == "coast/ledger"
    assert "mail" not in snap


def test_a_node_is_viewed_from_its_nexus(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    snap = snapshot(root, home, "ledger")
    assert snap["chair"] == "coast/ledger"
    assert snap["view"] == "coast"
    assert snap["briefing"]["address"] == "coast/ledger"
    assert snap["briefing"]["kind"] == "node"
    assert [step["name"] for step in snap["path"]] == ["coast", "ledger"]
    deep = snapshot(root, home, "dock")
    assert deep["view"] == "harbor"
    assert [step["name"] for step in deep["path"]] == ["coast", "harbor", "dock"]
    assert [section["name"] for section in deep["board"]["sections"]] == ["harbor"]


def test_the_open_chair_keeps_its_own_cards(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    status_put(root, home, "ledger", "Count the tide", ["counted"], [], [])
    inbox = root / "ledger" / "inbox"
    inbox.mkdir()
    (inbox / "letter.md").write_text("hello\n", encoding="utf-8")
    snap = snapshot(root, home, "ledger", today=date(2026, 10, 3))
    own = snap["briefing"]["attention"]
    assert sorted(card["kinds"] for card in own) == [["inbox"], ["unaccounted"]]
    assert {card["address"] for card in own} == {"coast/ledger"}
    assert not [card for card in snap["attention"] if card.get("address") == "coast/ledger"]
    assert snap["nexus"]["address"] == "coast"
    assert "children" not in snap["nexus"]
    top = snapshot(root, home, "coast", today=date(2026, 10, 3))
    assert top["briefing"]["attention"] == []
    assert len([card for card in top["attention"] if card.get("address") == "coast/ledger"]) == 2


def test_titles_come_from_project_yaml(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    write_project(root / "ledger", {"name": "ledger", "title": "The Tide Ledger", "services": ["status", "mail"]})
    write_project(root, {"name": "coast", "title": "Coast Office", "services": ["status", "mail"]})
    status_put(root, home, "ledger", "Count the tide", ["counted"], [], [])
    inbox = root / "ledger" / "inbox"
    inbox.mkdir()
    (inbox / "letter.md").write_text("hello\n", encoding="utf-8")
    snap = snapshot(root, home, "ledger", today=date(2026, 10, 3))
    coast = snap["tree"][0]
    assert (coast["name"], coast["title"]) == ("coast", "Coast Office")
    assert coast["children"][0]["title"] == "harbor"
    assert coast["children"][1]["title"] == "The Tide Ledger"
    assert [step["title"] for step in snap["path"]] == ["Coast Office", "The Tide Ledger"]
    assert snap["briefing"]["title"] == "The Tide Ledger"
    assert snap["nexus"]["title"] == "Coast Office"
    harbor, own = snap["board"]["sections"]
    assert (harbor["title"], own["title"]) == ("harbor", "Coast Office")
    assert own["this_week"][0]["title"] == "The Tide Ledger"
    assert {card["title"] for card in snap["briefing"]["attention"]} == {"The Tide Ledger"}


def test_overlay_inbox_and_disagreement(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    status_put(root, home, "ledger", "Count the tide", ["counted"], [], [])
    overlay = root / "_contextforge" / "workspaces" / "ledger"
    _local(overlay, "Walk the tide line")
    inbox = overlay / "inbox"
    inbox.mkdir(parents=True)
    (inbox / "letter.md").write_text("hello\n", encoding="utf-8")
    (inbox / "_log.md").write_text("log\n", encoding="utf-8")
    (inbox / "README.md").write_text("read\n", encoding="utf-8")
    (inbox / "_archive").mkdir()
    detail = node_detail(root, home, "coast", "ledger")
    assert detail["ok"] is True
    assert detail["diverged"] is True
    assert detail["differs"][0] == "forefront"
    assert detail["local"]["forefront"] == "Walk the tide line"
    assert detail["published"]["forefront"] == "Count the tide"
    assert detail["inbox_count"] == 1
    snap = snapshot(root, home, "coast")
    health = _health(snap, "coast/ledger")
    assert health["signals"] == ["inbox", "drift"]
    assert health["drift"] is True
    assert health["inbox"] == 1
    card = next(item for item in snap["attention"] if item.get("address") == "coast/ledger" and "text" not in item)
    assert card["kinds"] == ["inbox"]
    assert card["inbox"] == 1
    chore = next(item for item in snap["housekeeping"]["cards"] if item.get("address") == "coast/ledger")
    assert chore["kinds"] == ["drift"]
    assert snap["inbox_count"] == 1


def test_matching_local_file_is_not_a_split(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    status_put(
        root, home, "ledger",
        "Count the tide",
        ["counted yesterday"],
        ["count again"],
        [],
        repo="main · clean",
    )
    _local(root / "ledger", "Count the tide")
    detail = node_detail(root, home, "coast", "coast/ledger")
    assert detail["diverged"] is False
    assert detail["differs"] == []
    assert detail["inbox_count"] == 0


def test_markup_alone_is_not_drift(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    status_put(
        root, home, "ledger",
        "Count the tide in tide.md",
        ["counted yesterday"],
        ["count again"],
        ["The tide book is late. See the almanac."],
        repo="main · clean",
    )
    _local(
        root / "ledger",
        "Count the tide in `tide.md`",
        loops=["**The tide book is late.** See [the almanac](https://example.com/almanac)."],
    )
    detail = node_detail(root, home, "coast", "coast/ledger")
    assert detail["diverged"] is False


def test_age_and_forefront_dates_are_not_signals(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    for board in (root / "FOCUS.md", root / "harbor" / "FOCUS.md"):
        board.write_text("# FOCUS\nupdated: 2026-10-03\n\n## This week\n", encoding="utf-8")
    status_put(root, home, "ledger", "Count the tide", [], [], [])
    status_put(root, home, "dock", "Paint before 2020-01-01, see `specs/2020-01-01-paint.md`", [], [], [])
    later = snapshot(root, home, "coast", today=date.today() + timedelta(days=30))
    ledger = _health(later, "coast/ledger")
    assert ledger["state"] == "up_to_date"
    assert ledger["age_days"] == 30
    assert "stale" not in ledger
    assert not [item for item in later["attention"] if item.get("address") == "coast/ledger" and "text" not in item]
    assert _health(later, "harbor/dock")["state"] == "up_to_date"


def test_a_waiting_letter_is_listed_but_does_not_color_the_chair(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    for board in (root / "FOCUS.md", root / "harbor" / "FOCUS.md"):
        board.write_text("# FOCUS\nupdated: 2026-10-03\n\n## This week\n", encoding="utf-8")
    status_put(root, home, "ledger", "Count the tide", ["counted yesterday"], ["count again"], [], repo="main · clean")
    _local(root / "ledger", "Count the tide")
    inbox = root / "ledger" / "inbox"
    inbox.mkdir()
    (inbox / "letter.md").write_text("hello\n", encoding="utf-8")
    snap = snapshot(root, home, "coast")
    health = _health(snap, "coast/ledger")
    assert (health["state"], health["inbox"]) == ("up_to_date", 1)
    card = next(card for card in snap["attention"] if card.get("address") == "coast/ledger")
    assert (card["class"], card["kinds"]) == ("notice", ["inbox"])
    assert card["fixes"][0]["command"] == "process the inbox"


def test_a_chair_that_owes_a_sitrep_and_has_none_is_housekeeping(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    snap = snapshot(root, home, "coast")
    harbor = _health(snap, "harbor")
    assert harbor["state"] == "housekeeping"
    assert harbor["signals"] == ["no_sitrep"]
    chore = next(item for item in snap["housekeeping"]["cards"] if item["address"] == "harbor")
    assert chore["class"] == "housekeeping"
    assert chore["fixes"][0]["command"] == "/settle"


def test_a_chair_that_does_not_publish_is_neither(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    with (root / "nexus.md").open("a", encoding="utf-8") as handle:
        handle.write("| shed | shed/ | node | active | no | no | none | storage |\n")
        handle.write("| loft | loft/ | node | parked | no | no | none | old |\n")
    (root / "shed").mkdir()
    (root / "loft").mkdir()
    snap = snapshot(root, home, "coast")
    assert _health(snap, "coast/shed")["state"] == "no_publish"
    assert _health(snap, "coast/loft")["state"] == "no_publish"
    everything = snap["attention"] + snap["housekeeping"]["cards"]
    assert not [card for card in everything if card.get("address") in ("coast/shed", "coast/loft")]


def test_every_signal_has_a_class_and_a_fix(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    (root / "FOCUS.md").write_text(
        "# FOCUS\nupdated: 2026-10-03\n\n## This week\n\n"
        "1. **Mind the ledger** · due: 2026-10-01 · node: ledger\n"
        "2. **Sweep the quay** · due: 2026-09-30 · node: none\n",
        encoding="utf-8",
    )
    status_put(root, home, "ledger", "Count the tide", ["counted yesterday"], ["count again"], [], repo="main · clean")
    _local(root / "ledger", "Walk the tide line")
    note_post(root, home, chair="coast", intended_for="coast/ledger", inbox="ledger/inbox/letter.md", why="deliver")
    inbox = root / "ledger" / "inbox"
    inbox.mkdir()
    (inbox / "letter.md").write_text("hello\n", encoding="utf-8")
    snap = snapshot(root, home, "coast", today=date(2026, 10, 3))

    line = next(card for card in snap["attention"] if card.get("text") == "Mind the ledger")
    assert line["class"] == "needs_you"
    assert line["kinds"] == ["date_passed", "unaccounted"]
    passed, missing = line["fixes"]
    assert (passed["by"], passed["command"], passed["folder"]) == ("you", "weekly review", "coast")
    assert "coast/ledger" in missing["step"]

    quay = next(card for card in snap["attention"] if card.get("text") == "Sweep the quay")
    assert quay["kinds"] == ["date_passed"]
    assert quay["address"] is None and quay["board"] == "coast"

    letters = next(card for card in snap["attention"] if card.get("address") == "coast/ledger" and "text" not in card)
    assert letters["kinds"] == ["inbox"]
    assert letters["class"] == "notice"
    assert letters["fixes"][0] == {
        "kind": "inbox", "by": "you", "command": "process the inbox",
        "folder": "coast/ledger", "step": "Say process the inbox in coast/ledger.",
    }

    chore = next(card for card in snap["housekeeping"]["cards"] if card.get("address") == "coast/ledger")
    assert chore["class"] == "housekeeping"
    assert chore["kinds"] == ["drift", "mail"]
    assert {fix["by"] for fix in chore["fixes"]} == {"agent"}
    assert {fix["command"] for fix in chore["fixes"]} == {"/settle"}
    assert "/settle-pass all from coast" in chore["fixes"][0]["step"]

    summary = snap["housekeeping"]
    # Ledger, plus the three chairs that owe a sitrep and have none.
    assert {card["address"] for card in summary["cards"]} == {"coast", "harbor", "harbor/dock", "coast/ledger"}
    assert summary["count"] == 4
    assert (summary["fix"]["command"], summary["fix"]["folder"]) == ("/settle-pass all", "coast")

    assert _health(snap, "coast/ledger")["state"] == "needs_you"
    assert _health(snap, "coast")["state"] == "needs_you"  # the quay line sits on its board


def test_settle_wait_leftovers_land_on_the_chair_they_name(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path, harbor_sensitive=True)
    overlay = root / "_contextforge" / "workspaces" / "coast"
    overlay.mkdir(parents=True)
    (overlay / "settle-wait.md").write_text(
        "\n".join([
            "---",
            "title: Settle wait",
            "target: all",
            "date: 2026-10-25",
            "---",
            "",
            "# Settle wait",
            "",
            "## coast/ledger",
            "- surface: Open loops",
            "- line: Ask the harbor master",
            "- why: only copy",
            "- surface: Next steps",
            "- line: Recount the tide",
            "- why: no home",
            "",
            "## dock",
            "- surface: Open loops",
            "- line: a private detail",
            "- why: only copy",
            "",
            "## The Old Pier",
            "- surface: Forefront",
            "- line: Mend the pier",
            "- why: no home",
            "",
        ]) + "\n",
        encoding="utf-8",
    )
    snap = snapshot(root, home, "coast", today=date(2026, 10, 3))

    ledger = _health(snap, "coast/ledger")
    assert (ledger["waiting"], ledger["state"]) == (2, "needs_you")
    card = next(card for card in snap["attention"] if card.get("address") == "coast/ledger" and "text" not in card)
    assert card["kinds"] == ["waiting"]
    assert [item["line"] for item in card["items"]] == ["Ask the harbor master", "Recount the tide"]
    assert {item["date"] for item in card["items"]} == {"2026-10-25"}
    assert card["fixes"][0]["folder"] == "coast"

    dock = next(card for card in snap["attention"] if card.get("address") == "harbor/dock")
    assert dock["sensitive"] is True
    assert (dock["waiting"], dock["items"]) == (1, [])

    # Coast is the open chair, so its own card rides with the briefing.
    pier = next(card for card in snap["briefing"]["attention"] if "waiting" in card["kinds"])
    assert pier["items"][0]["heading"] == "The Old Pier"


def test_desk_count_skips_readme_archive_and_hidden_files(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    desk = root / "desk"
    (desk / "_archive").mkdir(parents=True)
    for name in ("one.md", "two.md", "README.md", ".hidden", "desktop.ini"):
        (desk / name).write_text("x\n", encoding="utf-8")
    (desk / "_archive" / "old.md").write_text("x\n", encoding="utf-8")
    snap = snapshot(root, home, "coast")
    assert _health(snap, "coast")["desk"] == 2
    assert _health(snap, "coast/ledger")["desk"] == 0
    assert "desk" not in [kind for card in snap["attention"] for kind in card["kinds"]]


def test_sensitive_nexus_marks_its_chairs_and_board(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path, harbor_sensitive=True)
    snap = snapshot(root, home, "coast")
    harbor = snap["tree"][0]["children"][0]
    assert harbor["sensitive"] is True
    assert harbor["children"][0]["sensitive"] is True
    assert snap["board"]["sections"][0]["sensitive"] is True
    assert snap["next"]["sensitive"] is True
    assert snap["board"]["sections"][1]["sensitive"] is False


def test_a_sensitive_chair_publishing_less_is_not_drift(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path, harbor_sensitive=True)
    status_put(root, home, "dock", "Paint the dock", [], [], [])
    _local(root / "harbor" / "dock", "Paint the dock", loops=["a private detail"])
    detail = node_detail(root, home, "coast", "harbor/dock")
    assert detail["sensitive"] is True
    assert detail["diverged"] is False
    assert _health(snapshot(root, home, "coast"), "harbor/dock")["drift"] is False


def test_since_skips_an_unchanged_snapshot(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    first = snapshot(root, home, "coast")
    same = snapshot(root, home, "coast", since=first["version"])
    assert same == {"ok": True, "unchanged": True, "version": first["version"]}
    status_put(root, home, "ledger", "Count the tide", [], [], [])
    moved = snapshot(root, home, "coast", since=first["version"])
    assert moved["version"] != first["version"]
    assert "tree" in moved


def test_snapshot_does_not_ack_mail(root: Path, home: Path) -> None:
    write_map(
        root,
        [
            {"name": "nexus", "inbox": True, "description": "Nexus", "status": "active"},
            {"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"},
        ],
    )
    write_project(root, {"name": "nexus", "services": ["status", "mail"]})
    write_project(root / "harbor", {"name": "harbor", "services": ["mail"]})
    (root / "FOCUS.md").write_text(
        "# FOCUS\nupdated: 2026-10-05\n\n## This week\n\n1. **Chart the harbor** · due: none · node: harbor\n",
        encoding="utf-8",
    )
    posted = note_post(
        root, home, chair="harbor",
        intended_for="nexus", inbox="inbox/letter.md", why="export",
    )
    note_id = posted["note"]["id"]
    snap = snapshot(root, home, "nexus")
    assert snap["mail_unacked"] == 1
    assert _addresses(snap["tree"]) == ["nexus", "harbor"]
    assert snap["next"]["text"] == "Chart the harbor"
    saved = json.loads((home / "mail" / f"{note_id}.json").read_text(encoding="utf-8"))
    assert saved["ack"] is None


def test_on_its_own_a_fix_names_no_command(root: Path, home: Path) -> None:
    write_map(
        root,
        [
            {"name": "nexus", "inbox": True, "description": "Nexus", "status": "active"},
            {"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"},
        ],
    )
    write_project(root, {"name": "nexus", "services": ["status", "mail"]})
    write_project(root / "harbor", {"name": "harbor", "services": ["mail"]})
    snap = snapshot(root, home, "nexus")
    assert _health(snap, "harbor")["state"] == "no_publish"
    chore = snap["housekeeping"]["cards"][0]
    assert chore["kinds"] == ["no_sitrep"]
    assert chore["fixes"][0]["command"] is None
    assert chore["fixes"][0]["step"] == "Write this chair's status file and publish it."
    assert snap["housekeeping"]["fix"]["command"] is None


def _get(port: int, path: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as res:
            return res.status, res.read()
    except urllib.error.HTTPError as err:
        return err.code, b""


def test_page_serves_on_localhost(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    httpd = make_server(root, home, 0)
    assert httpd.server_address[0] == "127.0.0.1"
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = httpd.server_address[1]
        status, page = _get(port, "/")
        assert status == 200
        assert b'id="app"' in page
        status, script = _get(port, "/app.js")
        assert status == 200
        assert b"/vendor/preact-htm.js" in script
        assert _get(port, "/vendor/preact-htm.js")[0] == 200
        status, body = _get(port, "/api/snapshot")
        assert json.loads(body)["chair"] == "coast"
        status, body = _get(port, "/api/snapshot?chair=nowhere")
        assert json.loads(body)["error"] == "unknown_chair"
        assert _get(port, "/vendor/README.md")[0] == 404
        assert _get(port, "/../pyproject.toml")[0] == 404
        try:
            second = make_server(root, home, port)
        except OSError:
            second = None
        assert second is None, "a second page bound a port that is already serving"
    finally:
        httpd.shutdown()
        thread.join(timeout=5)
        httpd.server_close()


def test_envoy_waits_its_turn_to_serve_the_page(tmp_path: Path, home: Path, monkeypatch, capfd) -> None:
    monkeypatch.delenv("ENVOY_VIEW", raising=False)
    root = _coast(tmp_path)
    holder = make_server(root, home, 0)
    port = holder.server_address[1]
    stop = threading.Event()
    thread = keep_page_up(root, home, port=port, retry=0.05, stop=stop)
    assert thread is not None
    try:
        time.sleep(0.2)
        assert thread.is_alive(), "a taken port ended the wait"
        holder.server_close()
        body = b""
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                status, body = _get(port, "/api/snapshot")
                if status == 200:
                    break
            except OSError:
                time.sleep(0.05)
        assert json.loads(body)["chair"] == "coast"
    finally:
        stop.set()
        thread.join(timeout=5)
    assert not thread.is_alive()
    assert capfd.readouterr().out == ""


def test_the_page_can_be_turned_off(tmp_path: Path, home: Path, monkeypatch) -> None:
    monkeypatch.setenv("ENVOY_VIEW", "off")
    assert keep_page_up(_coast(tmp_path), home, port=0) is None
