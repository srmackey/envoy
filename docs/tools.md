# Tools

Fifteen tools. Every call takes `chair`. Without `nexus.md` that is `nexus` or a name on the map. With `nexus.md` it is an address: the nexus's own name, or `nexus/node`.

Every tool sets `openWorldHint` false. None of these tools use the network.

| Kind | readOnlyHint | destructiveHint | idempotentHint |
|---|---|---|---|
| Read | true | false | true |
| Create | false | false | false |
| Write | false | false | true |
| Delete | false | true | true |

| Tool | Kind | What it does | Side effects |
|---|---|---|---|
| `map_list` | Read | Read the roster. A nexus caller also sees each node's identity file when that file exists. | Reads `MAP.md`, or that nexus's `nexus.md` when the bulletin root has one. |
| `map_upsert` | Write | Create or replace one map row. Nexus only. | Writes that same file. |
| `status_put` | Write | Publish this chair's sitrep. | Overwrites that chair's document in the vault. |
| `status_get` | Read | Read a published sitrep. A node reads its own. Nexus reads children that opted in. | Reads the vault. |
| `note_post` | Create | Create a mail note. The author is the calling chair. | Writes a new note in the vault. A repeat creates another. Does not write the letter file. |
| `note_list` | Write | Open mail notes this chair can see. | The first time the intended chair lists a note, writes an ack of shown. |
| `note_ack` | Write | Set the ack on a note this chair can see. | Writes that note. |
| `note_gate` | Write | Set the gate on a note. Nexus only. | Writes that note. |
| `note_remove` | Delete | Delete a note this chair authored. | Removes that note from the vault. A second call finds it already gone. |
| `now_view` | Write | Read the board of the nexus this chair sits in. A nexus caller also gets direct-chair sitreps, reconcile, and open mail. | Reads `FOCUS.md`. A nexus call writes an ack of shown on notes intended for that chair. A node call only reads. |
| `agenda_post` | Create | Post one agenda row. With `due` it is a calendar item, and `until` makes it a window. Without `due` it is a task at the bottom of the list. The author is the calling chair. | Writes a new row in the root nexus's store. A repeat creates another. |
| `agenda_update` | Write | Change the text or dates of a row. The author, or the root nexus. An empty `due` turns a calendar item back into a task. | Writes that row. |
| `agenda_close` | Write | Close a row. The author, or the root nexus. | Stamps the row closed. It stays on disk and leaves every list. A second call changes nothing. |
| `agenda_reorder` | Write | Move named tasks to the top of the task list in that order. Root nexus only. | Rewrites the rank on tasks whose place changed. |
| `agenda_list` | Read | The calendar by bucket and the task list in order, for the whole install or only this chair's rows. | Reads the root nexus's store. Never closes a row. |

A tool add, remove, or rename updates this file and `CHANGELOG.md` in the same change.
