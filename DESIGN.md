# Envoy

**Version 0.4**

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

**Status.** One vault document per subscriber. Publish overwrites. Not a queue, not acked. The local digest is the node's record. The vault document is the sitrep the parent reads. Ordinary chairs publish the whole digest. Discreet chairs publish a thin sitrep. Subscriber articles: `provisions/articles/methodology/envoy-status.md` and the discreet variant on the chair's map, not in this repo's extract list.

**Mail.** The note is a bell. The letter is the inbox file. Nodes never write another node's inbox. The nexus chair is the only deliverer. Subscriber article: `provisions/articles/methodology/envoy-mail.md`.

## Chair identity

Every tool takes `chair`. When `nexus.md` is present, `chair` is an address: the nexus's own name, or `nexus/node`. `nexus` still names the root nexus. A bare name that matches one node is that node. An ambiguous bare name is `unknown_chair`. A two-segment address whose second part is itself a nexus does not resolve. When `nexus.md` is absent, `chair` is `nexus` or a `MAP.md` name. Envoy trusts `chair` (local single-user). Unknown chairs fail with `unknown_chair`.

## Living NOW

Durable `FOCUS.md` changes only when the operator ranks it. Living NOW is a nexus query: that file, plus published sitreps of this nexus's direct chairs, plus open mail notes. Listing that mail records an ack of shown when the note is intended for the calling chair. The page counts unseen notes and does not record that ack. The hole in the board stays empty until the operator steers. A node call returns the board of the nexus that contains the node. When `nexus.md` sets `focus:` to a direct child, the result includes that child's board as `focus`, and that child is left out of the chair lines.

Reconcile (nexus, against a ranked line at `node: A`):

Normalize whitespace. Board substance is the one-line text of the ranked item. The current check compares words: case and punctuation do not count.

- `current` if the Forefront and the board substance use the same words, or one of them adds at most four words and the other adds none.
- `accounted` if the board substance appears in the joined Where I left off text.
- `satisfied` if it appears in the published `repo:` line. Not a flag.
- `no_trail` if A has no sitrep (flag: setup gap).
- `unaccounted` otherwise (flag).
- Lines with `node: none` are not reconciled.

Envoy does not infer synonyms. A line with words of its own stays `unaccounted`.

Always-on names come from the Always-on column of the nexus whose board is on screen. Without `nexus.md`, they come from `always-on.yaml`. `now_view` reports `always_on_missing` for names with no This-week line on that board. It does not invent lines.

## Local page

The server serves one page on `127.0.0.1` while it runs. Each host starts its own server process, and they share one port: the first to bind it serves the page, and the rest try again every thirty seconds, so the page stays up while any of them is running. The page thread writes nothing to stdout, which carries the MCP protocol. `envoy view` serves the same page without the tools. `ENVOY_VIEW=0` turns the page off and `ENVOY_VIEW_PORT` moves it.

The page reads the same board, roster, and published sitreps as the tools, plus `_status/STATUS.md`, the pending files in `inbox/`, and the files in `desk/` on each chair. When `_contextforge/workspaces/<folder name>/` is present, status and inbox are read there instead; the desk is always the chair's own folder. When `nexus.md` is present, the page also reads `settle-wait.md` from each nexus's overlay: what a settle pass could not clear, one section per chair. It counts unseen mail notes and never lists them, so viewing does not mark a note seen.

The chair you open leads, in the wide column: its Forefront, then its repo, age, and desk chips and any housekeeping on it, then what on that chair needs you, then where it left off, its next steps, and its open loops. The nexus it sits in is the narrower column beside it, or below it on a narrow screen: one line for the housekeeping under it with the command that clears it, then its board with the first line marked as the next move, then everything else under it that needs you. Opening a nexus uses the same two columns, with its own sitrep on the left and its board on the right. The `focus:` child's board comes first on a nexus that sets one.

Every signal belongs to whoever clears it. Needs you: a board line whose date has passed, a board line its chair's sitrep does not reflect, an always-on gap, and an item a settle pass left waiting. Housekeeping, which an agent settling that chair clears without asking: a published sitrep that differs from the local file, an unseen mail note, and an active chair that owes a sitrep and has none. A waiting inbox letter is listed under needs you with no color: processing it is yours, but a letter is not a warning. Everything else is state in plain text, such as when a chair last updated, a coming due date, a dirty repo, and the desk count. Nothing goes stale by age, and dates inside a Forefront are not read as deadlines. Inline markup and links do not count as disagreement. A signal about the open chair shows on that chair, and the nexus shows the rest, so nothing appears twice.

Each signal carries how it clears: who clears it, the step, and the command, behind an info mark that opens on hover, keyboard focus, or a tap, with a button to copy the command. When `nexus.md` is present, the step names the command and the folder to run it in: `/settle` in the chair or `/settle-pass all` in the nexus for housekeeping, `weekly review` for board lines, `process the inbox` for letters. Without it, the step says the same job in plain words.

A chair's name on the page is the `title:` in its `project.yaml`, or its folder name when it has none. Addresses stay folder names, and Jump matches either.

The tree shows every chair with a colored circle: green when it is up to date, blue for housekeeping, amber when something on it needs you, and gray when its registry row does not list `status`, so it publishes no sitrep. A board line counts toward the chair it names, whichever nexus's board holds it. Inbox, mail, and desk counts sit beside the name. The selection lives in the address bar, so links and the back button work.

A sensitive chair's content stays hidden until you show it. Its published sitrep is not compared with its local file, because it publishes less on purpose, and a settle pass's leftovers on it show only as a count.

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
