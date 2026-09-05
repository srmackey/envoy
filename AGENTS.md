# AGENTS.md — Envoy

Canonical constitution for the Envoy server repo. Claude loads it via the thin `CLAUDE.md` shim. Edit this file, never the shim.

**Product.** Envoy is a local MCP server for the bulletin's bulletin: membership, published status, mail notes, and syos notes. Files stay the record for `MAP.md`, `NOW.md`, local STATUS, and inbox letters. Envoy is the bus and the vault. Complementary to the guidance store (situated identity) and the workspace memory (dev context). Not a second brain. Not the nexus.

**Design lock.** `DESIGN.md` is the locked spec (v0.2, syos amended 2026-09-05). Implement against it. Nested nexuses, services beyond status/mail/syos, and grandchild map types wait for an explicit design change.

**Session entry.** Read `_status/STATUS.md` and state the Forefront before other work. Live next-step lives there, not in this file.

## Agent stance

You are a careful steward of a small, local bulletin MCP. the bulletin files on disk are the record for the map and the board. The vault holds published sitreps, mail notes, and syos notes. Prefer the existing tools (`map_*`, `status_*`, `note_*`, `syos_*`, `now_view`) before adding new ones.

## Stack

- Python 3.11+, `uv`, FastMCP, Pydantic v2, PyYAML
- `MAP.md` is YAML at the the bulletin root. `NOW.md` is markdown there.
- Vault is JSON files under `ENVOY_HOME` (default `~/.envoy`)
- Tests with pytest under `tests/`
- `uv sync` / `uv run pytest` / `uv run envoy`

## Invariants

- Every tool takes `chair`: `nexus` or a `MAP.md` `name`. Envoy trusts `chair` (local single-user). Chairs must send their own name.
- `MAP.md` is the one roster. The vault does not keep a second copy.
- Published status, mail notes, and syos notes live only in the vault, not in the the bulletin tree.
- Syos is a self-addressed brief. The note is the payload. No inbox file. No nexus gate. A chair writes only to itself. `now_view` does not include syos.
- `status_put` overwrites that chair's document. Not a queue. No ack.
- Mail is a queue. The note is not the letter. The letter is the inbox file.
- Nodes never write another node's inbox. Envoy does not deliver letters; the nexus chair does.
- Sensitive grain is a chair duty on publish, not an Envoy content filter. Tests use fictional chairs only.
- the bulletin root is `ENVOY_ROOT` or `--root` (required). Vault is `ENVOY_HOME` or `--vault` (default `~/.envoy`).

## Layout (this repo)

| Path | Role |
|------|------|
| `DESIGN.md` | Locked design spec |
| `src/envoy/` | Server package |
| `tests/` | pytest |
| `install/` | MCP host snippets (not user-vault data) |
| `inbox/` | Node arrival tray. Process on command. |
| `_status/STATUS.md` | Nexus-facing where / next (local; not shipped) |

## Status

`_status/STATUS.md` is the digest. Do not turn it into the life board.

## Human-sounding

the guidance store `interaction/human-sounding`. Prose an agent will follow must read like a competent human wrote it. No em-dashes or en-dashes as rhetorical separators.
