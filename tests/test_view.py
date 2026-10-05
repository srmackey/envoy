"""The local page reads the bulletin and does not mark mail seen."""

from __future__ import annotations

import json
from pathlib import Path

from tests.conftest import write_map, write_project

from envoy.notes_store import note_post
from envoy.status_store import status_put
from envoy.view import board_snapshot, node_detail
from envoy.view_server import make_server


def _coast(tmp_path: Path) -> Path:
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


def _local(folder: Path, forefront: str) -> None:
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
            "- count again",
            "",
            "## Open loops",
            "",
        ]) + "\n",
        encoding="utf-8",
    )


def test_board_reads_focus_child_and_opens_a_nexus(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    status_put(root, home, "ledger", "Count the tide", ["counted"], [], [])
    snap = board_snapshot(root, home, "coast")
    assert snap["ok"] is True
    assert snap["chair"] == "coast"
    assert snap["parent"] is None
    assert snap["focus"]["node"] == "harbor"
    assert snap["focus"]["this_week"][0]["text"] == "Paint the dock"
    assert snap["now"]["this_week"][0]["due"] == "2026-10-04"
    names = {entry["name"]: entry for entry in snap["entries"]}
    assert names["harbor"]["opens"] is True
    assert names["coast/ledger"]["opens"] is False
    assert {row["node"] for row in snap["forefronts"]} == {"coast/ledger"}
    assert "mail" not in snap


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
    assert detail["local"]["forefront"] == "Walk the tide line"
    assert detail["published"]["forefront"] == "Count the tide"
    assert detail["inbox_count"] == 1


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
    assert detail["inbox_count"] == 0


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
    snap = board_snapshot(root, home, "nexus")
    assert snap["mail_unacked"] == 1
    saved = json.loads((home / "mail" / f"{note_id}.json").read_text(encoding="utf-8"))
    assert saved["ack"] is None


def test_page_serves_on_localhost(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    httpd = make_server(root, home, 0)
    assert httpd.server_address[0] == "127.0.0.1"
    thread_started = False
    import threading

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    thread_started = True
    try:
        import urllib.request

        port = httpd.server_address[1]
        page = urllib.request.urlopen(f"http://127.0.0.1:{port}/").read().decode("utf-8")
        assert "This week" in page or "refresh" in page
        payload = json.loads(
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/board").read().decode("utf-8")
        )
        assert payload["chair"] == "coast"
        missing = json.loads(
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/node?chair=coast&node="
            ).read().decode("utf-8")
        )
        assert missing["error"] == "invalid_payload"
    finally:
        if thread_started:
            httpd.shutdown()
            thread.join(timeout=5)
            httpd.server_close()
