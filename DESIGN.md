# Envoy — Design Spec

**Version 0.2 · amended 2026-09-08** (mail visibility, outstanding notice, list auto-ack; reconcile `satisfied` / `no_trail`). Syos amended 2026-09-05. v0.1 locked 2026-08-25.

**Status:** accepted 2026-08-25 (the operator). Syos slice accepted 2026-09-05. Mail visibility and outstanding notice accepted 2026-09-08. Product name Envoy.

---

## 1. Purpose

Envoy is a local MCP server for the bulletin's bulletin: a thin bus plus reader.

It holds membership (`MAP.md` librarian), published status (vault sitreps), mail notes (bells for inbox letters), and syos notes (self-addressed briefs). Local files stay the record for the map, `NOW.md`, local `STATUS.md`, and inbox letters. Status is not a conversation. Mail is. Syos is a one-shot brief a chair leaves for its next sitting.

It is not the guidance store (situated identity). It is not the dev-context server (dev context). It is not the workspace memory (chair memory). It is not the nexus chair. The nexus chair still gates mail and ranks the board.

---

## 2. Settled decisions

Locked 2026-08-19, except where the 2026-08-25 recut replaces them. Recut items are marked. Product name and home locked 2026-08-25.

1. One thin the bulletin MCP: bus plus reader. Product name **Envoy**. Sibling node `envoy/`. Files stay the record for map, `NOW.md`, local `STATUS.md`, and inbox letters.
2. One structured map in the whole system. Public address book. Persisted as `MAP.md` at the bulletin root. Envoy is the librarian (read and write). `AGENTS.md` is gate rules, not a second roster.
3. Each node keeps a hardcopy identity in `project.yaml`. Category lives there. Senders do not stamp category on notes. Nexus uses `bulletin/project.yaml` with `name: nexus`.
4. **Recut 2026-08-25.** Status and mail are the first two **services**. A node opts in. Opt-in means that node takes the subscriber contract for that service (§5.3, §5.4). Later message types are more services, not more fields on these two. Each new service ships its own contract.
5. Nodes may write `bulletin/inbox/` and post a `mail` note (`intended_for` is a guess). Nodes never write another node's inbox. Nexus is the gate and the only deliverer into a node inbox.
6. **Recut 2026-08-25.** Status is not ephemeral notes and not a queue. For a subscriber, one STATUS document is always present in the Envoy vault. Content updates as the node works. The node also keeps local `STATUS.md` as its record and publishes that digest into the vault (`repo:` when present, four sections). Nexus reads the vault. It does not poll node files and does not ack/remove status. The pack still presents Forefront and `repo:`, and uses Where I left off to reconcile. It does not paste Next steps or Open loops.
7. **Recut 2026-08-25.** Durable `NOW.md` changes only when the operator steers. Living NOW is awareness: what he ranked vs what children currently report. The hole stays empty until he steers. The agent does not fill This week from status.
8. **Recut 2026-08-25.** Living NOW is a query: current `NOW.md`, plus published STATUS for opted-in children, plus open `mail` notes. Reconcile per §7.1. Do not flag when the trail accounts for a ranked line. Flag when it does not.
9. Uncertainty is first-class. Nexus reads the letter and the destination, then delivers or fouls. the operator decides fouls. A foul can become a gate patch later, or confirm the gate was right.
10. A node posts a `mail` note after it writes the nexus inbox file. Nexus writes `deliver` files into node inboxes. The handoff file is the wake-up on the node side.
11. Once this bus is live, nexus awareness no longer reads node STATUS files. Session start is `now_view` plus inbox count. That was the reason `STATUS.md` stayed at project root. Local STATUS may then follow the owner-roots convention (`_status/`), same class as the inbox overlay. The path change is a status-contract patch, not an Envoy change. Until then the record path is `<node>/STATUS.md`.
12. **Locked 2026-08-25.** Nested nexuses are a lens, not this implementation. A nexus that is also a node still only behaves as a node to its parent. No grandchildren. A parent may not even know a child is itself a nexus. Same node contract at every edge. What a child publishes upward is one sitrep (and mail as itself), never its internals.
13. **Locked 2026-09-05.** Syos is the third service. Own contract, own tools, own vault subtree. Not a `kind` on mail. The note is the payload (no inbox file). A chair writes only to itself. Nexus does not list other chairs' syos. `now_view` does not include syos. The machine is the tools in §8. The chair contract is `methodology/envoy-syos`.

Superseded 2026-08-25 (do not implement): status as note kind `done` / `forefront` / `heat` / `rank`; event-driven pin then ack then remove; living NOW built from open status notes; nexus NOW-broadcast as status notes.

---

## 3. Surfaces

| Surface | Record | Who writes | Envoy |
|---|---|---|---|
| Map | `bulletin/MAP.md` | Envoy (nexus chair calling map tools) | Read/write the file |
| Node identity | `<node>/project.yaml`; nexus: `bulletin/project.yaml` | That chair | Read to join for a nexus caller |
| Durable NOW | `bulletin/NOW.md` | Nexus chair, when the operator steers | Read to join living NOW |
| Local status | `<node>/STATUS.md` until this bus is live; then owner-roots `_status/` | That node | Not stored. Node writes the file, then publishes sitrep |
| Published status | Envoy vault, one document per status subscriber | That node, via status tools | Owns the store. Overwrites on publish |
| Mail letters | `inbox/` files | Node → nexus inbox; nexus → node inbox after gate | Notes point at the file |
| Mail notes | Envoy vault | Chairs via note tools | Owns the store. Queued until processed |
| Syos notes | Envoy vault | That chair, via syos tools | Owns the store. The note is the brief |

`MAP.md` is a the bulletin file. Envoy does not keep a second copy. Published status, mail notes, and syos notes live in the Envoy vault, not in the the bulletin tree.

---

## 4. The map

### 4.1 `MAP.md`

Path: `bulletin/MAP.md`.

One row per tracked node, plus a `nexus` row. Untracked trees are absent.

```yaml
# MAP.md is YAML so Envoy can read and write it without a private schema.
updated: 2026-08-25
entries:
  - name: nexus
    inbox: true
    description: the bulletin post office and board
    status: active
  - name: family
    inbox: true
    description: Family family process
    status: active
```

| Field | Values |
|---|---|
| `name` | Folder key, or `nexus` |
| `inbox` | `true` / `false` |
| `description` | One line, enough to guess `intended_for` |
| `status` | `active` / `parked` / `superseded` |

`status: parked` means do not route new work here. `superseded` keeps the name addressable.

When the registry changes (new sibling, disposition, inbox added), the nexus chair updates the map through Envoy in that same sitting.

### 4.2 `project.yaml`

Path: `<node>/project.yaml`. The node owns it. Nexus: `bulletin/project.yaml`.

```yaml
name: family
description: Family family process
category: family
inbox: true
status: active
services:
  - status
  - mail
```

`category` is a node fact (for example `family`, `career`, `scripture`, `tooling`, `memory`). Nexus may read it via the Envoy join. It is not a sender field on notes.

`services` is the opt-in list. Values: `status`, `mail`, `syos`. Absent list means not subscribed. A later type is another entry, not a change to these.

Nexus `AGENTS.md` keeps privacy, routing triggers, and foul rules. It points at `MAP.md` for membership and does not restate the roster.

### 4.3 How a chair sees the map

The intended path is always `map_list`. A node does not open `MAP.md` as its API.

- Node caller: rows from `MAP.md` as stored.
- Nexus caller: same rows, each joined with that chair's `project.yaml` when the file exists (`category` and `services` included). Missing `project.yaml` is not an error; joined fields are omitted for that row.

Folder for a map `name`: the bulletin root for `nexus`, else `<root>/<name>/`.

---

## 5. Services

### 5.1 Status (published sitrep)

Always-present for a subscriber. One document per node. Publish overwrites. Not a queue. Not acked. Not removed after a nexus visit.

**Local file** is the node's record (`STATUS.md`, later `_status/` per owner roots). **Vault document** is the published sitrep. For an ordinary chair it is the same digest. For a discreet chair it is a thin sitrep, not a copy of the local file. Nexus reads the vault instead of polling the file.

Published body (plus Envoy provenance: `node`, `version`, `author`, `updated` of this publish):

| Field | Meaning |
|---|---|
| `repo` | If present on the local file, directly under `updated:`. Same format as the local `repo:` line (§5.3). Do not invent. Omit when the node has no `repo:` line |
| Forefront | One line |
| Where I left off | 2–4 lines. The trail for reconcile |
| Next steps | Ordered working list |
| Open loops | Waiting-on items, pending decisions |

**Store vs pack.** The vault holds the whole digest. Living NOW / session-start pack still presents Forefront, the `repo:` line when present (indented, as today), and uses Where I left off only to reconcile ranked lines. Do not paste Next steps or Open loops onto the pack.

Two the guidance store subscriber contracts, same Envoy service (`status` in `project.yaml`):

- `methodology/envoy-status`: publish the whole digest.
- `methodology/envoy-status-discreet`: publish a thin sitrep (one-line Forefront, optional `repo:`, trail only as needed for board reconcile, empty Next steps and Open loops). Local STATUS may stay richer. The article does not name which chairs are sensitive.

A node without `status` in `services` has no vault document. Nexus does not expect one.

### 5.2 Mail (queue)

Ephemeral notes. Shared author envelope. Nexus gate stamps are nexus-only. This service is settled as drafted 2026-08-19.

#### Envelope (author writes)

| Field | Meaning |
|---|---|
| `id` | Envoy-assigned UUID4 hex |
| `kind` | `mail` |
| `author` | `nexus` or a map `name` |
| `created` | ISO datetime UTC |
| `ack` | Empty until a reader writes it |

`ack` shape: `{ chair, time, action }`. `action` is a short token: `shown`, `ignored`, `delivered`, `held`.

#### Body

| Field | Meaning |
|---|---|
| `intended_for` | Map `name` or `nexus` (a guess) |
| `inbox` | Path to the letter, relative to the bulletin root |
| `why` | For Y because… |

The note is not the letter.

#### Nexus gate stamp (not in the sender envelope)

After nexus considers a `mail` note and the letter:

| Field | Values |
|---|---|
| `gate` | `deliver` / `hold` / `foul` |
| `gate_note` | Optional. Why |

Envoy returns `gate` and `gate_note` only to a nexus caller. A node listing its own notes sees `ack`, not the gate.

#### Visibility and lifetime

- Nexus may list every open mail note.
- A node may list mail notes it authored, and mail notes where `intended_for` is that node.
- Only `author` may remove.
- Any chair that can see a note may write `ack`.
- `note_list` sets `ack` to `shown` when the calling chair is `intended_for` and the note has no ack yet. Listing as the intended chair is awareness. Nexus listing notes meant for other chairs does not auto-ack them. Explicit `note_ack` remains available for other actions.
- Acked notes may expire 14 days after the ack. Unacked notes and notes with `gate: foul` or `gate: hold` do not expire.

### 5.3 Status subscriber contract

What a chair takes on with `status` in `services`. Local files plus publish. This is the node-facing contract. The vault sitrep in §5.1 is what the parent reads.

**Local home.** Owner root `_status/`. Until the bus is live, the live path stays `<node>/STATUS.md` at project root so today's pack can still read Forefront. After the bus is live, move into `_status/` (status-contract path patch). Do not move before the bus is live.

**Local record.** The existing `STATUS.md` digest. Not a log of every task. Same shape after the path patch:

| Field | Grain |
|---|---|
| `updated:` | ISO date |
| `repo:` | If this node uses the repo ritual: `branch · clean\|dirty[ · WIP]`, directly under `updated:`. Do not invent |
| Forefront | One line. The next move |
| Where I left off | 2–4 lines. What changed, including ranked work that left the forefront |
| Next steps | Ordered working list |
| Open loops | Waiting-on items, pending decisions |

**Publish (ordinary).** `methodology/envoy-status`. After a real change (and on exit from a sitting that changed it): write the local file, then `status_put` the whole digest (`repo:` when present, four sections, provenance). The pack still does not print Next steps or Open loops (§5.1 store vs pack).

**Publish (discreet).** `methodology/envoy-status-discreet`. Write the local file as usual. `status_put` a thin sitrep only: one-line Forefront at nexus grain, `repo:` if present, trail only as needed to reconcile a ranked line (same grain), Next steps and Open loops empty. Do not copy or summarize the local working lists into the vault.

**Do not.** Do not enqueue status events. Do not expect an ack. Do not read sibling STATUS. A nexus that is also a node keeps this same local digest for *itself*, not a dump of its children.

**Parent side (not the subscriber, but the other half).** Nexus `status_get` / `now_view`, reconcile per §7.1. No drain.

### 5.4 Mail subscriber contract

What a chair takes on with `mail` in `services`. The inbox machine plus the note queue. Letter format and process ritual are below.

**Local home.** Inbox overlay. Live path is `inbox/`. Intended owner-root name is `_inbox/`; that rename is a separate explicit move, not this slice. The machine below is the contract regardless of folder name.

**Inbox machine** (every mail subscriber, including nexus):

```text
inbox/          # or _inbox/ after the rename
├── README.md   # one screen: what this inbox is, how to process
├── _log.md     # append-only: date, file, source, destination or hold
├── _archive/   # processed files move here; never silent delete
└── pending     # dumps or structured handoffs
```

Process on command only (`process the inbox`, or point at a file). Never on session start. Never because a file or note arrived. Propose as a group, wait, then file / hold / archive. Never silent delete. The receiving constitution maps the letter; the sender does not name paths inside the receiver.

**Send (node → nexus).** Propose-only: the agent may notice extra-project signal and propose. It does not auto-write the nexus inbox.

1. Write the letter into `bulletin/inbox/` (handoff schema, `kind: export`).
2. `note_post` the bell (`intended_for`, `inbox` path, `why`).
3. Later, when a result carries the note id under `mail_acked_authored` (or after `note_list` own notes shows an ack), persist anything still unpersisted, then `note_remove`.

**Receive (into this chair's inbox).** Only nexus writes a node inbox (`kind: deliver`). The note is the wake-up. `note_list` as this chair acks `shown` on notes meant for it. Process the letter on command under this constitution.

**Do not.** Do not write another node's inbox. Do not treat the note as the letter. Do not process because the bell rang.

**Nexus extra (gate, not a third service).** List open mail notes. Open the letter. Deliver / hold / foul. the operator decides holds and fouls. Ack after that decision. Sensitive delivery still needs his confirmation.

### 5.5 Syos (self-addressed brief)

Ephemeral notes. The note is the payload. No inbox file. No nexus gate. A chair writes only to itself.

Envoy does not care about the trigger phrase. The subscriber article does. This slice is the machine: post, list, ack, remove.

#### Envelope

| Field | Meaning |
|---|---|
| `id` | Envoy-assigned UUID4 hex |
| `kind` | `syos` |
| `author` | Forced to `chair` |
| `created` | ISO datetime UTC |
| `intended_for` | Forced to `chair`. A chair cannot syos another chair |
| `body` | The checkable brief. Required. Non-empty after strip |
| `ack` | Empty until a reader writes it |

`ack` shape: `{ chair, time, action }`. `action` is a short token (`shown`, `checked`, `ignored`, or whatever the article later names). Envoy stores it; it does not enumerate it.

#### Visibility and lifetime

- A chair lists only its own syos notes (`author == chair`).
- Nexus does not receive other chairs' syos. `now_view` does not include syos. Mail stays mail.
- Only `author` may remove.
- Any chair that can see a note may write `ack`.
- Acked notes may expire 14 days after the ack. Unacked notes do not expire.

### 5.6 Syos subscriber contract

What a chair takes on with `syos` in `services`. Vault only. No the bulletin file.

**Write.** `syos_post` with `body`. `author` and `intended_for` are this chair. A chair not opted in gets `not_subscribed`.

**Read.** `syos_list` this chair's open notes. Present them. Do not verify and do not continue the work because a note arrived. the operator chooses.

The the guidance store article that encodes this contract is `methodology/envoy-syos`.

---

## 6. Chair identity

Every MCP call sends `chair`: `nexus` or a `MAP.md` `name`.

This is a local single-user contract. Envoy trusts `chair`. Articles require a chair to send its own name. Author-remove, list filters, status overwrite, and gate visibility use this field.

Unknown `chair` (not `nexus` and not a map `name`): mutating tools return `ok: false`, `error: unknown_chair`. Read tools that only need `chair` for filtering treat it as a node with no extra rights.

---

## 7. Loops

### 7.1 Status

On a real change to the node's digest (status assessed, ranked work finished, new forefront):

1. The node updates local `STATUS.md` when that file is the record.
2. If it opted into `status`, it publishes the whole digest (`repo:` when present, four sections, provenance). The vault document for that node is replaced.
3. Nexus does not drain a queue. It reads each subscribed child's current document.

**Reconcile** (nexus, against durable `NOW.md`):

Let a This-week (or Later) line name work X at `node: A`. A's published forefront is now Z.

- If the trail **accounts for X** (done, dropped, or otherwise no longer the next move): living awareness shows X resolved and current Z. **Do not flag.** The hole in `NOW.md` stays until the operator steers.
- If the trail **does not account for X**: **flag**. Board and report disagree. Nexus does not guess why.

Absence of X from forefront is not enough. Forefront is only "pick this up next." The trail is what makes a missed sitting resolvable without a news feed.

Several publishes in one node sitting: only the last document is there. The trail on that document is the roll-up, not a replay of every intermediate forefront.

**Mechanical rule for `now_view` (locked 2026-08-25; `satisfied` / `repo:` added 2026-09-08):**

Normalize whitespace. Board substance is the one-line text of the ranked item (not the due/node suffix).

- `current` if A's published Forefront equals the board substance.
- `accounted` if not current and the board substance appears as a substring of the joined Where I left off text.
- `satisfied` if not current or accounted and the board substance appears as a substring of the published `repo:` line. Not a flag.
- `no_trail` if A has no published sitrep (flag: setup gap, not drift).
- `unaccounted` otherwise (flag).
- Lines with `node: none` are not reconciled against a child sitrep.

This is conservative. The chair may still explain a flag. Envoy does not infer synonyms. `stale_trail` and `drifted` wait; leftover mismatch stays `unaccounted`.

### 7.2 Mail, node → nexus

1. The node writes a handoff file into `bulletin/inbox/` (`kind: export`).
2. The node posts a `mail` note: `intended_for`, `inbox` path, `why`.
3. Nexus lists `mail` notes, opens the letter, looks up the destination (`MAP.md` + `project.yaml` + `AGENTS.md` gate).
4. Nexus chooses:
   - **deliver** — write a `deliver` handoff into that node's `inbox/`, set `gate: deliver`, ack `delivered`.
   - **hold** — no node-inbox write, `gate: hold`, loop the operator in. No ack yet.
   - **foul** — no node-inbox write, `gate: foul`, loop the operator in. No ack yet.
5. the operator decides a hold or foul: send, rewrite, drop, or patch the gate. Then nexus acks (`delivered`, `held`, or `ignored`).
6. The sending node later sees the ack and removes the note.

Process-on-command still applies to inbox files. The note is the bell. `process the inbox` (or pointing at a file) is still the ritual that files, redistributes, or archives the letter.

### 7.3 Living NOW

A nexus query, not a stored object:

1. Read `NOW.md`.
2. Read published STATUS for children opted into `status`. Reconcile per §7.1.
3. List open `mail` notes.
4. Present the durable week, then resolved ranked lines (not flags), `no_trail` and `unaccounted` (flags), current Forefronts with `repo:` when present, and waiting mail. Do not paste Next steps or Open loops. Where I left off is for reconcile, not a second board.

Nodes see NOW through `now_view`. They do not read sibling STATUS. "All nodes can see NOW" is the downward read. Aggregation of children is a nexus sitting.

### 7.4 Always-on nodes

`family` and `career` still require a This-week line on durable `NOW.md`. A resolved ranked line does not remove that requirement. Replacement is a steer, not an automatic promotion of the node's next Forefront.

`now_view` for a nexus caller includes `always_on_missing`: names in `{family, career}` with no This-week line. It does not invent lines.

### 7.5 Syos

1. A subscribed chair posts a syos note with `body`.
2. The sitting stops if its loaded snapshot is already stale.
3. A later sitting in that chair lists open syos notes and presents them.
4. the operator chooses to act, ack, or ignore. The agent does not act because the note arrived.
5. Author removes when done, or an acked note expires after 14 days.

This loop does not touch inbox files and does not go through the nexus gate.

---

## 8. MCP tools

| Tool | Chair | Does |
|---|---|---|
| `map_list` | any | Read `MAP.md`. Nexus caller gets `project.yaml` join |
| `map_upsert` | nexus | Create or replace one map row; write `MAP.md` |
| `status_put` | status subscriber | Publish this chair's sitrep. Overwrites that node's vault document. `author` forced to `chair` |
| `status_get` | any | Read published sitrep. A node reads its own. Nexus reads children who opted in |
| `note_post` | mail subscriber | Create a `mail` note. `author` is forced to `chair` |
| `note_list` | any | Open mail notes visible to `chair` |
| `note_ack` | any that can see the note | Set `ack` |
| `note_gate` | nexus | Set `gate` / `gate_note` on a `mail` note |
| `note_remove` | author | Delete the note |
| `now_view` | any | Read `NOW.md`. Nexus caller also receives published STATUS (reconciled) and open mail notes (living NOW). Node caller receives `NOW.md`. Does not include syos |
| `syos_post` | syos subscriber | Create a `syos` note. `author` and `intended_for` are forced to `chair`. `body` is the brief |
| `syos_list` | any | Open syos notes this chair authored (itself only) |
| `syos_ack` | any that can see the note | Set `ack` |
| `syos_remove` | author | Delete the note |

Unknown `intended_for` (not a map `name` and not `nexus`): accept the note, nexus treats it as `foul` when gated.

`note_post` of `mail` does not require the inbox file to exist at post time. Nexus gate treats a missing file as `foul`.

`status_put` from a chair not opted into `status` is an error. `note_post` from a chair not opted into `mail` is an error. `syos_post` from a chair not opted into `syos` is an error.

`map_upsert` from a non-nexus chair is `ok: false`, `error: nexus_only`. Same for `note_gate`.

`status_get`: node chair requesting a different node's sitrep is `ok: false`, `error: forbidden`. Nexus may read any opted-in child. A node may omit `node` and get its own.

Return shape: success includes `"ok": true`. Failures include `"ok": false` and `"error": <token>`. Tokens used in v0.1: `unknown_chair`, `nexus_only`, `not_subscribed`, `forbidden`, `missing_map`, `missing_root`, `missing_status`, `missing_note`, `not_author`, `invalid_payload`.

Every tool result also carries a chair-scoped mail notice (empty lists when quiet):

| Field | Meaning |
|---|---|
| `mail_unacked_for_me` | Ids of open mail notes where `intended_for` is the calling chair and `ack` is empty |
| `mail_acked_authored` | Ids of open mail notes this chair authored that now carry an `ack` |

Ids are enough to call `note_ack` or `note_remove` without a prior `note_list`. The notice is mail only; syos stays on `syos_list`.

---

## 9. Chair contracts (the guidance store)

The article bodies encode §5.3, §5.4, and §5.6. They are not a second contract. Same Envoy tools. Split 2026-08-25.

**`methodology/envoy-status`:** ordinary status subscriber. Publish the whole digest.

**`methodology/envoy-status-discreet`:** privacy-sensitive status subscriber. Local STATUS may be richer. Publish a thin sitrep only. Does not name which chairs are sensitive; the chair's map attaches this article.

**`methodology/envoy-mail`:** mail subscriber. Inbox machine plus `note_post`. Privacy-sensitive chairs keep `why` at summary-plus-pointer grain.

**`methodology/envoy-syos`:** syos subscriber. Self-addressed brief, no inbox file, no nexus gate. Write on the trigger phrase; read on session start and step-in; present and wait.

**Nexus (`methodology/nexus-board` + `methodology/nexus-handoff`):** session-start pack uses `now_view` plus inbox count; run the mail gate; do not invent rank; `map_upsert` when the registry changes; `AGENTS.md` points at `MAP.md` for membership.

**Node:** on step-in, if opted into status, read own local digest and `now_view`; if opted into mail, honor send/receive rules; if opted into syos, list open syos notes and present them, then wait. Never write a foreign node inbox. Never read sibling STATUS as an API.

Sensitive delivery still requires the operator's confirmation. That is a foul or hold until he says proceed.

`methodology/bulletin` is superseded. Do not attach it.

---

## 10. First implementation slice

1. MCP with the tools in §8, vault store for published STATUS and mail notes, `MAP.md` read/write.
2. Seed `MAP.md` from the current tracked roster. Seed `project.yaml` on each active node from that node's one-line description and service opt-in.
3. Point nexus `AGENTS.md` at `MAP.md` for membership.
4. the guidance store article patches in §9, rematerialize, new session.
5. Dogfood:
   - Status: node A publishes forefront X; later publishes Z with a trail that accounts for X; nexus `now_view` with NOW still on X resolves, no flag. A third publish to W with no trail mention of a ranked X flags.
   - Mail: one `mail` note plus nexus inbox file, one foul, one deliver.

---

## 11. Future lens (not this implementation)

A nexus of nexuses uses the same node contract at every edge. Each nexus knows only its children. It does not see grandchildren. A child that is itself a nexus has already folded its purview into one sitrep before publishing. Queue-of-events, if any, is how *this* nexus talks to *its* children for mail. It is not forwarded. Status upward is always the current document plus trail.

Do not implement nested nexuses in the first slice. Do not add a grandchild type to the map.

---

## 12. Implementation locks (v0.1)

Closed 2026-08-25. These were open on accept as details, not design forks.

1. **Home.** This product tree is its own git repo. the bulletin root is supplied at runtime (`ENVOY_ROOT` / `--root`), not by nesting this tree under another project.
2. **the bulletin root.** `ENVOY_ROOT` environment variable, or CLI `--root`. Required. No parent-directory walk (sources/live must not guess). Tests pass an explicit tmp root.
3. **Vault.** `ENVOY_HOME` environment variable, or CLI `--vault`. Default `~/.envoy`. JSON files, three subtrees:
   - `status/<name>.json` — one document per status subscriber
   - `mail/<id>.json` — one file per mail note
   - `syos/<id>.json` — one file per syos note
4. **`MAP.md` format.** YAML, fields as §4.1. Not Markdown-with-frontmatter in v0.1.
5. **`version` on status.** Envoy assigns an integer. First `status_put` for a node is `1`. Each overwrite adds 1. Chairs do not send `version`.
6. **Note ids.** UUID4 hex, no dashes.
7. **Timestamps.** UTC ISO-8601 with `Z`.
8. **Stack.** Python 3.11+, `uv`, FastMCP, Pydantic v2, PyYAML, pytest. Functions first; FastMCP tools are thin wrappers. Same error-dict style as the guidance store (`ok` / `error` token).
9. **Seed opt-in (first slice).** Active tracked nodes plus nexus get `status` and `mail`. Superseded map rows have no `project.yaml` (or empty `services`). Untracked trees are absent from `MAP.md`.
10. **Tests.** Fictional chairs only (`harbor`, `river`, `nexus`). No real sensitive node text in fixtures.

---

## 13. Out of scope for v0.2

- Nested nexuses and grandchild map types
- Owner-roots path move (`inbox/` → `_inbox/`)
- Extra services beyond status, mail, and syos
- Filtering or redacting published bodies
- Remote multi-user auth (chair is trusted)
- Installing Envoy as an the guidance store pack
