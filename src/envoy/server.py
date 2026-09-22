"""FastMCP server. Tools are thin wrappers over the shipped functions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from envoy.mapfile import map_list as map_list_fn
from envoy.mapfile import map_upsert as map_upsert_fn
from envoy.notes_store import note_ack as note_ack_fn
from envoy.notes_store import note_gate as note_gate_fn
from envoy.notes_store import note_list as note_list_fn
from envoy.notes_store import note_post as note_post_fn
from envoy.notes_store import note_remove as note_remove_fn
from envoy.notes_store import with_mail_notice
from envoy.now import now_view as now_view_fn
from envoy.status_store import status_get as status_get_fn
from envoy.status_store import status_put as status_put_fn

INSTRUCTIONS = """\
Envoy is a local bulletin MCP. Files stay the record for MAP.md, NOW.md, local STATUS, and inbox letters. Envoy stores published sitreps and mail notes. Every call sends chair (nexus or a MAP.md name). Session living NOW is now_view. map_list is the roster API. Do not poll sibling STATUS files once this server is live. Session briefs live on the chair-memory store, not here.
"""

mcp = FastMCP("Envoy", instructions=INSTRUCTIONS)

# Clients treat an unset hint as destructive and open to the network.
_READ = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}
_WRITE = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}
_CREATE = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": False,
    "openWorldHint": False,
}
_DELETE = {
    "readOnlyHint": False,
    "destructiveHint": True,
    "idempotentHint": True,
    "openWorldHint": False,
}

_root: Path | None = None
_home: Path | None = None


def set_context(root: Path, home: Path) -> None:
    global _root, _home
    _root = Path(root).resolve()
    _home = Path(home).resolve()


def _ctx() -> tuple[Path, Path]:
    if _root is None or _home is None:
        raise RuntimeError("set_context must run before tools")
    return _root, _home


def _result(chair: str, payload: dict[str, Any]) -> dict[str, Any]:
    _, home = _ctx()
    return with_mail_notice(payload, home, chair)


@mcp.tool(annotations=_READ)
def map_list(chair: str) -> dict[str, Any]:
    """Read MAP.md. Nexus caller gets project.yaml join."""
    root, _ = _ctx()
    return _result(chair, map_list_fn(root, chair))


@mcp.tool(annotations=_WRITE)
def map_upsert(
    chair: str,
    name: str,
    inbox: bool,
    description: str,
    status: str,
) -> dict[str, Any]:
    """Create or replace one map row and write MAP.md. Nexus only."""
    root, _ = _ctx()
    return _result(
        chair,
        map_upsert_fn(
            root,
            chair,
            {
                "name": name,
                "inbox": inbox,
                "description": description,
                "status": status,
            },
        ),
    )


@mcp.tool(annotations=_WRITE)
def status_put(
    chair: str,
    forefront: str,
    where_i_left_off: list[str],
    next_steps: list[str],
    open_loops: list[str],
    repo: str | None = None,
) -> dict[str, Any]:
    """Publish this chair's sitrep. Overwrites that node's vault document."""
    root, home = _ctx()
    return _result(
        chair,
        status_put_fn(
            root,
            home,
            chair,
            forefront,
            where_i_left_off,
            next_steps,
            open_loops,
            repo=repo,
        ),
    )


@mcp.tool(annotations=_READ)
def status_get(chair: str, node: str | None = None) -> dict[str, Any]:
    """Read a published sitrep. A node reads its own. Nexus reads opted-in children."""
    root, home = _ctx()
    return _result(chair, status_get_fn(root, home, chair, node=node))


@mcp.tool(annotations=_CREATE)
def note_post(
    chair: str,
    intended_for: str,
    inbox: str,
    why: str,
) -> dict[str, Any]:
    """Create a mail note. Author is forced to chair."""
    root, home = _ctx()
    return _result(chair, note_post_fn(root, home, chair, intended_for, inbox, why))


@mcp.tool(annotations=_WRITE)
def note_list(chair: str) -> dict[str, Any]:
    """Open mail notes visible to chair."""
    root, home = _ctx()
    return _result(chair, note_list_fn(root, home, chair))


@mcp.tool(annotations=_WRITE)
def note_ack(chair: str, note_id: str, action: str) -> dict[str, Any]:
    """Set ack on a mail note this chair can see."""
    root, home = _ctx()
    return _result(chair, note_ack_fn(root, home, chair, note_id, action))


@mcp.tool(annotations=_WRITE)
def note_gate(
    chair: str,
    note_id: str,
    gate: str,
    gate_note: str | None = None,
) -> dict[str, Any]:
    """Set gate and optional gate_note on a mail note. Nexus only."""
    root, home = _ctx()
    return _result(
        chair,
        note_gate_fn(root, home, chair, note_id, gate, gate_note=gate_note),
    )


@mcp.tool(annotations=_DELETE)
def note_remove(chair: str, note_id: str) -> dict[str, Any]:
    """Delete a mail note this chair authored."""
    root, home = _ctx()
    return _result(chair, note_remove_fn(root, home, chair, note_id))


@mcp.tool(annotations=_READ)
def now_view(chair: str) -> dict[str, Any]:
    """Read NOW.md. Nexus also receives living NOW: sitreps, reconcile, and open mail."""
    root, home = _ctx()
    return _result(chair, now_view_fn(root, home, chair))


def run(root: Path, home: Path) -> None:
    set_context(root, home)
    mcp.run()
