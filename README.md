# Envoy

Envoy is a local MCP server for a bulletin: membership (`MAP.md`), published status, and mail notes. Files on disk stay the record for the map, `NOW.md`, local status, and inbox letters. The vault holds published sitreps and mail notes. Envoy is the bus and the vault. It is not a wiki, not standing guidance, and not the nexus chair. Session briefs are not this server.

A clone can run it against any bulletin root. Wire it into a larger system, or use it on its own.

## Stack

- Python 3.11+, `uv`, FastMCP, Pydantic v2, PyYAML
- `MAP.md` and `NOW.md` at the bulletin root (`ENVOY_ROOT`)
- Vault JSON under `ENVOY_HOME` (default `~/.envoy`)
- Tests with pytest under `tests/`

## Setup

```bash
uv sync
uv run pytest
uv run envoy --root /path/to/bulletin
```

| Variable | Role |
|---|---|
| `ENVOY_ROOT` | Bulletin root (required; or pass `--root`) |
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

How it is structured: [`DESIGN.md`](DESIGN.md). What moved: [`CHANGELOG.md`](CHANGELOG.md).

## Tests

Fixtures and examples use fictional chairs only. Do not publish real sitreps or letters into a shared vault from test runs.
