# Envoy

**Version 0.3**

Envoy is a local MCP server for a bulletin: membership, published status, and mail notes. Files on disk stay the record for the map, the board, local status, and inbox letters. The vault holds published sitreps and mail notes. Envoy is the bus and the vault. It is not a wiki, not standing guidance, not chair memory, and not the nexus chair. Session briefs are not this server.

Someone who has never sat here should be able to read this file and see how the pieces fit. Locked implementer detail lives in chair overlay, not here.

## Surfaces

The bulletin root is `ENVOY_ROOT` (or `--root`). Required. The vault is `ENVOY_HOME` (or `--vault`, default `~/.envoy`).

| Surface | Record | Who writes |
|---|---|---|
| Map | `MAP.md` at the bulletin root | Envoy, when the nexus chair calls map tools |
| Node identity | `<node>/project.yaml`; nexus: `<root>/project.yaml` | That chair |
| Durable board | `NOW.md` at the bulletin root | The nexus chair, when the operator ranks it |
| Always-on chairs | `always-on.yaml` at the bulletin root | Instance config, not product source |
| Local status | `_status/STATUS.md` on that chair | That node |
| Published status | Vault `status/<name>.json` | That node, via status tools |
| Mail letters | `inbox/` files | Node to the nexus inbox; nexus into a node inbox after the gate |
| Mail notes | Vault `mail/<id>.json` | Chairs via note tools |

`MAP.md` lives on disk at the bulletin root. Envoy does not keep a second copy. Published sitreps and mail notes live only in the vault.

## Map

`MAP.md` is YAML. One row per tracked node, plus a `nexus` row. Untracked trees are absent.

Each row has `name`, `inbox`, `description`, and `status` (`active` / `parked` / `superseded`). `parked` means do not route new work there. `superseded` keeps the name addressable.

`project.yaml` is the node's hardcopy: `category` and `services` live there. `services` is the opt-in list (`status`, `mail`). Absent list means not subscribed. Leftover `syos` is ignored.

The intended read is always `map_list`. A node caller gets the stored rows. A nexus caller gets the same rows joined with each chair's `project.yaml` when that file exists.

Folder for a map `name`: the bulletin root for `nexus`, else `<root>/<name>/`.

## Services

A node opts in. Later message types are more services, not more fields on these two.

**Status.** One vault document per subscriber. Publish overwrites. Not a queue, not acked. The local digest is the node's record. The vault document is the sitrep the parent reads. Ordinary chairs publish the whole digest. Discreet chairs publish a thin sitrep. Subscriber articles: `articles/methodology/envoy-status.md` and the discreet variant on the chair's map, not in this repo's extract list.

**Mail.** The note is a bell. The letter is the inbox file. Nodes never write another node's inbox. The nexus chair is the only deliverer. Subscriber article: `articles/methodology/envoy-mail.md`.

## Chair identity

Every tool takes `chair`: `nexus` or a `MAP.md` `name`. Envoy trusts `chair` (local single-user). Unknown mutating chairs fail with `unknown_chair`.

## Living NOW

Durable `NOW.md` changes only when the operator ranks it. Living NOW is a nexus query: that file, plus published sitreps, plus open mail notes. The hole in the board stays empty until the operator steers.

Reconcile (nexus, against a ranked line at `node: A`):

Normalize whitespace. Board substance is the one-line text of the ranked item.

- `current` if A's published Forefront equals the board substance.
- `accounted` if the board substance appears in the joined Where I left off text.
- `satisfied` if it appears in the published `repo:` line. Not a flag.
- `no_trail` if A has no sitrep (flag: setup gap).
- `unaccounted` otherwise (flag).
- Lines with `node: none` are not reconciled.

Envoy does not infer synonyms. Leftover mismatch is `unaccounted`.

Always-on names come from `always-on.yaml`. `now_view` reports `always_on_missing` for names listed there with no This-week line. It does not invent lines.

## Tools

| Tool | Chair | Does |
|---|---|---|
| `map_list` | any | Read `MAP.md`. Nexus caller gets `project.yaml` join |
| `map_upsert` | nexus | Create or replace one map row; write `MAP.md` |
| `status_put` | status subscriber | Publish this chair's sitrep. Overwrites that node's vault document |
| `status_get` | any | Read a published sitrep. A node reads its own. Nexus reads opted-in children |
| `note_post` | mail subscriber | Create a mail note. Author is forced to `chair` |
| `note_list` | any | Open mail notes visible to `chair` |
| `note_ack` | any that can see the note | Set `ack` |
| `note_gate` | nexus | Set `gate` / `gate_note` on a mail note |
| `note_remove` | author | Delete the note |
| `now_view` | any | Read `NOW.md`. Nexus also receives living NOW |

Every tool result carries a chair-scoped mail notice: `mail_unacked_for_me` and `mail_acked_authored`.

Success includes `"ok": true`. Failures include `"ok": false` and `"error": <token>`.

## Out of scope

- Nested nexuses and grandchild map types
- Extra services beyond status and mail
- Filtering or redacting published bodies
- Remote multi-user auth
- Session-brief tools on this server
