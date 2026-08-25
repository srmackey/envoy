# Envoy

Envoy is a local MCP server for the bulletin's bulletin: membership (`MAP.md`), published status, and mail notes. Files on disk stay the record for the map, `NOW.md`, local `STATUS.md`, and inbox letters. The vault holds published sitreps and mail notes only. Envoy is the bus and the vault, complementary to the guidance store and the workspace memory. It is not a second brain and not the nexus chair.

## Stack

- Python 3.11+, `uv`, FastMCP, Pydantic v2, PyYAML
- `MAP.md` and `NOW.md` at the the bulletin root
- Vault JSON under `ENVOY_HOME` (default `~/.envoy`)
- Tests with pytest under `tests/`

## Setup

```bash
uv sync
uv run pytest
uv run envoy --root <bulletin>
```

| Variable | Role |
|---|---|
| `ENVOY_ROOT` | the bulletin root (required; or pass `--root`) |
| `ENVOY_HOME` | Vault root (default `~/.envoy`; or pass `--vault`) |

MCP host snippets: [`install/mcp.json.examples.md`](install/mcp.json.examples.md).

## Tools

| Tool |
|---|
| `map_list` |
| `map_upsert` |
| `status_put` |
| `status_get` |
| `note_post` |
| `note_list` |
| `note_ack` |
| `note_gate` |
| `note_remove` |
| `now_view` |

Locked behavior and chair rules: [`DESIGN.md`](DESIGN.md) (v0.1).

## Tests

Fixtures and examples use fictional chairs only. Do not publish real sitreps or letters into a shared vault from test runs.
