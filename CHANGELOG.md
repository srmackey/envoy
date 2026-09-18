# Changelog

All notable changes to Envoy are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Changed

- Public docs, CLI copy, and package description no longer name an instance. The bulletin root is `ENVOY_ROOT` / `--root`.
- `DESIGN.md` is the public presentation. Implementer spec lives in chair overlay.
- Public contract 0.2.1: mail writes the letter through the overlay home. It does not name a store.
- Public contract 0.2.2: the nexus mail article is `methodology/post-office` (was `methodology/nexus-handoff`).

## [0.3.0] - 2026-09-17

### Removed

- Session-brief tools on this server. Session briefs live on the chair-memory store.

### Changed

- Always-on chairs are `always-on.yaml` at the bulletin root, not hardcoded.
- Install MCP snippets use path placeholders.
- Hygiene hook matches denylist terms as whole tokens.

### Added

- Public subscriber articles in `articles/`, listed by `provisions/pack.yaml`.

## [0.2.0] - 2026-09-08

### Added

- Mail notice on every tool result (`mail_unacked_for_me`, `mail_acked_authored`).
- Reconcile state `satisfied` when the board line appears in the published `repo:` field.
- Reconcile state `no_trail` when a ranked node has no sitrep.

## [0.1.0] - 2026-08-25

### Added

- Map, published status, mail notes, and `now_view`.
