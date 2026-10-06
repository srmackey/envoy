# Envoy

**Version 0.3**

Envoy is a local MCP server for a bulletin: membership, published status, and mail notes. Files on disk stay the record for the map, the board, local status, and inbox letters. The vault holds published sitreps and mail notes. Envoy is the bus and the vault. It is not a wiki, not standing guidance, not chair memory, and not the nexus chair. Session briefs are not this server.

Someone who has never sat here should be able to read this file and see how the pieces fit. Locked implementer detail lives in chair overlay, not here.

## Surfaces

The bulletin root is `ENVOY_ROOT` (or `--root`). Required. When that folder has `nexus.md`, each nexus folder holds its records in `_envoy/`, and `ENVOY_HOME` is not the record store. When it does not, the vault is `ENVOY_HOME` (or `--vault`, default `~/.envoy`) and `MAP.md` is the roster.

| Surface | Record | Who writes |
|---|---|---|
| Map | `MAP.md` at the bulletin root | Envoy, when the nexus chair calls map tools |
| Node identity | `<node>/project.yaml`; nexus: `<root>/project.yaml` | That chair |
| Durable board | `FOCUS.md` at the nexus root. Without `nexus.md`, `FOCUS.md` at the bulletin root. A leftover `NOW.md` is read only when `FOCUS.md` is absent | The nexus chair, when the operator ranks it |
| Always-on chairs | The Always-on column in `nexus.md`. Without that file, `always-on.yaml` at the bulletin root | Instance config, not product source |
| Local status | `_status/STATUS.md` on that chair | That node |
| Published status | That nexus's `_envoy/status/<folder basename>.json`. The document's `node` is the address | That node, via status tools |
| Mail letters | `inbox/` files | Node to the nexus inbox; nexus into a node inbox after the gate |
| Mail notes | That nexus's `_envoy/mail/<id>.json`. A note between two nexuses is stored in both | Chairs via note tools |

`MAP.md` lives on disk at the bulletin root when `nexus.md` is absent. Envoy does not keep a second copy of the roster. When `nexus.md` is present, `map_list` reads that nexus's nodes table. A child nexus is named by its own name. A node is `nexus/node`. `map_upsert` updates status and triggers on that same file, for that nexus's own rows. Published sitreps and mail notes live only in the vault.

## Map

`MAP.md` is YAML. One row per tracked node, plus a `nexus` row. Untracked trees are absent.

Each row has `name`, `inbox`, `description`, and `status` (`active` / `parked` / `superseded`). `parked` means do not route new work there. `superseded` keeps the name addressable.

`project.yaml` is the node's hardcopy: `category` and `services` live there. `services` is the opt-in list (`status`, `mail`). Absent list means not subscribed. Leftover `syos` is ignored.

The intended read is always `map_list`. A node caller gets the stored rows. A nexus caller gets the same rows joined with each chair's `project.yaml` when that file exists.

Folder for a map `name`: when `nexus.md` is absent, the bulletin root for `nexus`, else `<root>/<name>/`. When `nexus.md` is present, the folder is the one that file's path column names.

## Services

A node opts in. Later message types are more services, not more fields on these two.

**Status.** One vault document per subscriber. Publish overwrites. Not a queue, not acked. The local digest is the node's record. The vault document is the sitrep the parent reads. Ordinary chairs publish the whole digest. Discreet chairs publish a thin sitrep. Subscriber articles: `articles/methodology/envoy-status.md` and the discreet variant on the chair's map, not in this repo's extract list.

**Mail.** The note is a bell. The letter is the inbox file. Nodes never write another node's inbox. The nexus chair is the only deliverer. Subscriber article: `articles/methodology/envoy-mail.md`.

## Chair identity

Every tool takes `chair`. When `nexus.md` is present, `chair` is an address: the nexus's own name, or `nexus/node`. `nexus` still names the root nexus. A bare name that matches one node is that node. An ambiguous bare name is `unknown_chair`. A two-segment address whose second part is itself a nexus does not resolve. When `nexus.md` is absent, `chair` is `nexus` or a `MAP.md` name. Envoy trusts `chair` (local single-user). Unknown chairs fail with `unknown_chair`.

## Living NOW

Durable `FOCUS.md` changes only when the operator ranks it. Living NOW is a nexus query: that file, plus published sitreps of this nexus's direct chairs, plus open mail notes. The hole in the board stays empty until the operator steers. A node call returns the board of the nexus that contains the node. When `nexus.md` sets `focus:` to a direct child, the result includes that child's board as `focus`, and that child is left out of the chair lines.

Reconcile (nexus, against a ranked line at `node: A`):

Normalize whitespace. Board substance is the one-line text of the ranked item.

- `current` if A's published Forefront equals the board substance.
- `accounted` if the board substance appears in the joined Where I left off text.
- `satisfied` if it appears in the published `repo:` line. Not a flag.
- `no_trail` if A has no sitrep (flag: setup gap).
- `unaccounted` otherwise (flag).
- Lines with `node: none` are not reconciled.

Envoy does not infer synonyms. Leftover mismatch is `unaccounted`.

Always-on names come from the Always-on column of the nexus whose board is on screen. Without `nexus.md`, they come from `always-on.yaml`. `now_view` reports `always_on_missing` for names with no This-week line on that board. It does not invent lines.

## Local page

`envoy view` serves one page on `127.0.0.1`. It reads the same board, roster, and published sitreps as the tools, plus `_status/STATUS.md` and the pending files in `inbox/` on each chair. When `_contextforge/workspaces/<folder name>/` is present, those two paths are read there instead. It counts unseen mail notes and never lists them, so viewing does not mark a note seen.

The page opens on the next move: the first line of the board in view, which is the `focus:` child's board when one is set. Under it is one card per thing that needs you: a board line overdue or due within seven days, a line its chair's sitrep does not reflect, an always-on gap, unseen mail, inbox letters, and a chair whose local file and published sitrep disagree. Inline markup and links do not count as disagreement.

The tree shows every chair with a health dot: up to date, stale (sitrep older than seven days, or a Forefront date already past), files disagree, or no sitrep. Stale is shown, not raised as a card. Selecting a chair shows its briefing and moves the board to that chair's nexus. The selection lives in the address bar, so links and the back button work.

A sensitive chair's content stays hidden until you show it. Its published sitrep is not compared with its local file, because it publishes less on purpose.

The page is static files in the package with Preact vendored, no build step, and no outside requests. One endpoint returns the whole snapshot with a version. The page asks every two seconds and redraws only when the version changes.

## Tools

| Tool | Chair | Does |
|---|---|---|
| `map_list` | any | Read the roster (`nexus.md` when present, otherwise `MAP.md`). Nexus caller gets `project.yaml` join |
| `map_upsert` | nexus | Create or replace one row on that nexus's roster |
| `status_put` | status subscriber | Publish this chair's sitrep. Overwrites that node's vault document |
| `status_get` | any | Read a published sitrep. A node reads its own. Nexus reads opted-in children |
| `note_post` | mail subscriber | Create a mail note. Author is forced to `chair` |
| `note_list` | any | Open mail notes visible to `chair` |
| `note_ack` | any that can see the note | Set `ack` |
| `note_gate` | root nexus | Set `gate` / `gate_note` on a mail note |
| `note_remove` | author | Delete the note |
| `now_view` | any | Read `FOCUS.md` for the nexus this chair sits in. A nexus also receives living NOW for its direct chairs |

Every tool result carries a chair-scoped mail notice: `mail_unacked_for_me` and `mail_acked_authored`.

Success includes `"ok": true`. Failures include `"ok": false` and `"error": <token>`.

## Out of scope

- Addresses with more than one slash
- Extra services beyond status and mail
- Filtering or redacting published bodies
- Remote multi-user auth
- Session-brief tools on this server
