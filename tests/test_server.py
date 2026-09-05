import asyncio
from pathlib import Path

from tests.conftest import write_map, write_project

from envoy import server
from envoy.server import map_list as tool_map_list
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


def test_tools_use_process_context(root: Path, home: Path) -> None:
    write_map(root, [{"name": "harbor", "inbox": True, "description": "Harbor", "status": "active"}])
    write_project(
        root / "harbor",
        {
            "name": "harbor",
            "description": "Harbor",
            "category": "tooling",
            "inbox": True,
            "status": "active",
            "services": ["status"],
        },
    )
    set_context(root, home)
    listed = tool_map_list(chair="nexus")
    assert listed["ok"] is True
    put = tool_status_put(
        chair="harbor",
        forefront="X",
        where_i_left_off=["a"],
        next_steps=[],
        open_loops=[],
    )
    assert put["ok"] is True
