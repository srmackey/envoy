# Changelog

All notable changes to Envoy are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [0.4.0] - 2026-10-08

### Added

- A localhost page that leads with the chair you open (its Forefront, what on it needs you, and its record) beside the nexus it sits in, with a tree of every chair and its health. The server serves it while it runs; when several hosts run Envoy, one serves and the others take over if it exits. `ENVOY_VIEW=0` turns it off, `ENVOY_VIEW_PORT` moves it, and `envoy view` serves it alone. Chairs show the `title:` from their `project.yaml`, or their folder name. A chair's briefing shows only the fields where its local file and published sitrep disagree. Sensitive chairs stay hidden until shown. The page does not list mail notes.
- When `nexus.md` is at the bulletin root, `chair` is an address and each nexus folder holds `_envoy/`. `nexus` still names the root. A unique bare name resolves. An ambiguous one is `unknown_chair`. Mail between nexuses is stored in both nexus homes. `map_list` and `map_upsert` use that nexus's `nexus.md`. Without the file, `MAP.md` and `ENVOY_HOME` are unchanged.
- Security policy: how to report a vulnerability, and what the local process can touch.
- The tool list and each tool's side effects live in `docs/tools.md`. The README states the trust boundary.

### Changed

- **Install reads `platforms.yaml`.** The procedure is `install/README.md`. One server block is upserted into each enabled host. The host file, the format, and the key come from the stored definition. With no environment file, user-global host config is not edited. This product ships no router.
- **Add, remove, and a moved checkout use that same pass.** Add puts the name on `enabled` and runs the pass for each installed public product. Remove lists this product's key and writes nothing on the dry run. The real remove deletes only that key. A moved checkout runs the pass again with the current path.
- The board file is `FOCUS.md`. `now_view` reads the board of the nexus the chair sits in. A nexus result lists that nexus's direct chairs. When `nexus.md` sets `focus:`, the named child's board is returned as `focus` and that child is left out of the chair lines. A leftover `NOW.md` is read only when `FOCUS.md` is absent. With `nexus.md`, always-on names come from that file's Always-on column.
- Public contract 0.2.3: a sensitive chair may send mail when its own constitution allows that write. The guard lives in that chair's mail article.
- Each tool sets read-only, destructive, idempotent, and open-world hints. None are open to the network. `note_list` is a write because the first listing by the intended chair records an ack of shown.
- Public contract 0.2.2: the nexus mail article is `methodology/post-office` (was `methodology/nexus-handoff`).

## [0.3.0] - 2026-09-17

### Removed

- Session-brief tools on this server. Session briefs live on the chair-memory store.

### Changed

- Always-on chairs are `always-on.yaml` at the bulletin root, not hardcoded.
- Install MCP snippets use path placeholders.
- Hygiene hook matches denylist terms as whole tokens.
- Public docs, CLI copy, and package description no longer name an instance. The bulletin root is `ENVOY_ROOT` / `--root`.
- `DESIGN.md` is the public presentation. Implementer spec lives in chair overlay.
- Public contract 0.2.1: mail writes the letter through the overlay home. It does not name a store.

### Added

- Public subscriber articles in `articles/`, listed by `provisions/pack.yaml`.
- Mail notice on every tool result (`mail_unacked_for_me`, `mail_acked_authored`).
- Reconcile state `satisfied` when the board line appears in the published `repo:` field.
- Reconcile state `no_trail` when a ranked node has no sitrep.

## [0.2.0] - 2026-09-05

### Added

- Session briefs as a third service on this server. Removed in 0.3.0.

## [0.1.0] - 2026-08-25

### Added

- Map, published status, mail notes, and `now_view`.
