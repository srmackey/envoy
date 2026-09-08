import asyncio
from pathlib import Path

from tests.conftest import write_map, write_project

from envoy import server
from envoy.notes_store import note_post
from envoy.server import map_list as tool_map_list
from envoy.server import note_list as tool_note_list
from envoy.server import set_context
from envoy.server import status_put as tool_status_put


REQUIRED = {
    "map_list",
    "map_upsert",
    "status_put",
    "status_get",
    "note_post",
    "note_list",
    "note_ack",
    "note_gate",
    "note_remove",
    "now_view",
    "syos_post",
    "syos_list",
    "syos_ack",
    "syos_remove",
}


def test_server_module_exports_run() -> None:
    assert callable(server.run)
    assert server.mcp.name == "Envoy"


def test_mcp_exposes_fourteen_tools() -> None:
    tools = asyncio.run(server.mcp.list_tools())
    names = {getattr(tool, "name", None) for tool in tools}
    assert names == REQUIRED


def _seed_mail(root: Path) -> None:
    write_map(
        root,
        [
            {"name": "nexus", "inbox": True, "description": "Nexus", "status": "active"},
            {"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"},
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


def test_tools_use_process_context(root: Path, home: Path) -> None:
    _seed_mail(root)
    set_context(root, home)
    listed = tool_map_list(chair="nexus")
    assert listed["ok"] is True
    assert listed["mail_unacked_for_me"] == []
    assert listed["mail_acked_authored"] == []
    put = tool_status_put(
        chair="harbor",
        forefront="X",
        where_i_left_off=["a"],
        next_steps=[],
        open_loops=[],
    )
    assert put["ok"] is True
    assert put["mail_unacked_for_me"] == []
    assert put["mail_acked_authored"] == []


def test_tool_results_carry_mail_notice(root: Path, home: Path) -> None:
    _seed_mail(root)
    set_context(root, home)
    posted = note_post(
        root, home, chair="nexus",
        intended_for="harbor", inbox="harbor/inbox/letter.md", why="deliver",
    )
    note_id = posted["note"]["id"]
    listed = tool_map_list(chair="harbor")
    assert listed["mail_unacked_for_me"] == [note_id]
    assert listed["mail_acked_authored"] == []
    notes = tool_note_list(chair="harbor")
    assert notes["notes"][0]["ack"]["action"] == "shown"
    assert notes["mail_unacked_for_me"] == []
    author_view = tool_map_list(chair="nexus")
    assert author_view["mail_acked_authored"] == [note_id]
