# AGENTS.md — Envoy

Canonical constitution for the Envoy server repo.

**Product.** Envoy is a local MCP server for a bulletin: membership, published status, mail notes, and syos notes. Files stay the record for `MAP.md`, `NOW.md`, local STATUS, and inbox letters. Envoy is the bus and the vault. Not a second brain. Not the nexus.

**Out of scope.** Nested nexuses, services beyond status/mail/syos, and grandchild map types.

## Agent stance

You are a careful steward of a small, local bulletin MCP. Files on disk at `ENVOY_ROOT` are the record for the map and the board. The vault holds published sitreps, mail notes, and syos notes. Prefer the existing tools (`map_*`, `status_*`, `note_*`, `syos_*`, `now_view`) before adding new ones.

## Stack

- Python 3.11+, `uv`, FastMCP, Pydantic v2, PyYAML
- `MAP.md` is YAML at the `ENVOY_ROOT` tree. `NOW.md` is markdown there.
- Vault is JSON files under `ENVOY_HOME` (default `~/.envoy`)
- Tests with pytest under `tests/`
- `uv sync` / `uv run pytest` / `uv run envoy`

## Invariants

- Every tool takes `chair`: `nexus` or a `MAP.md` `name`. Envoy trusts `chair` (local single-user). Chairs must send their own name.
- `MAP.md` is the one roster. The vault does not keep a second copy.
- Published status, mail notes, and syos notes live only in the vault, not in the bulletin tree.
- Syos is a self-addressed brief. The note is the payload. No inbox file. No nexus gate. A chair writes only to itself. `now_view` does not include syos.
- `status_put` overwrites that chair's document. Not a queue. No ack.
- Mail is a queue. The note is not the letter. The letter is the inbox file.
- Nodes never write another node's inbox. Envoy does not deliver letters; the nexus chair does.
- Sensitive grain is a chair duty on publish, not an Envoy content filter. Tests use fictional chairs only.
- Bulletin root is `ENVOY_ROOT` or `--root` (required). Vault is `ENVOY_HOME` or `--vault` (default `~/.envoy`).

## Layout (this repo)

| Path | Role |
|------|------|
| `DESIGN.md` | System presentation |
| `src/envoy/` | Server package |
| `tests/` | pytest |
| `install/` | MCP host snippets (not user-vault data) |
