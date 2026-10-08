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
    assert snap["attention"][0]["kinds"] == ["due", "unaccounted"]
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
    assert sorted(card["kinds"] for card in own) == [["due", "unaccounted"], ["inbox"]]
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
    assert health["state"] == "drift"
    assert health["inbox"] == 1
    card = next(item for item in snap["attention"] if item.get("address") == "coast/ledger" and "text" not in item)
    assert card["kinds"] == ["inbox", "drift"]
    assert card["inbox"] == 1
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


def test_old_sitrep_and_past_forefront_date_are_stale(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    status_put(root, home, "ledger", "Count the tide", [], [], [])
    status_put(root, home, "dock", "Paint before 2020-01-01", [], [], [])
    later = snapshot(root, home, "coast", today=date.today() + timedelta(days=30))
    ledger = _health(later, "coast/ledger")
    assert ledger["state"] == "stale"
    assert ledger["stale_reason"] == "old"
    assert ledger["age_days"] == 30
    assert not [item for item in later["attention"] if item.get("address") == "coast/ledger" and "text" not in item]
    now = snapshot(root, home, "coast")
    assert _health(now, "coast/ledger")["state"] == "fresh"
    assert _health(now, "harbor/dock")["stale_reason"] == "past_date"
    assert _health(now, "harbor")["state"] == "silent"


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
