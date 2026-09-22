# Tools

Ten tools. Every call takes `chair`: `nexus`, or a name on the map.

Every tool sets `openWorldHint` false. None of these tools use the network.

| Kind | readOnlyHint | destructiveHint | idempotentHint |
|---|---|---|---|
| Read | true | false | true |
| Create | false | false | false |
| Write | false | false | true |
| Delete | false | true | true |

| Tool | Kind | What it does | Side effects |
|---|---|---|---|
| `map_list` | Read | Read the roster. A nexus caller also sees each node's identity file when that file exists. | Reads `MAP.md`. |
| `map_upsert` | Write | Create or replace one map row. Nexus only. | Writes `MAP.md`. |
| `status_put` | Write | Publish this chair's sitrep. | Overwrites that chair's document in the vault. |
| `status_get` | Read | Read a published sitrep. A node reads its own. Nexus reads children that opted in. | Reads the vault. |
| `note_post` | Create | Create a mail note. The author is the calling chair. | Writes a new note in the vault. A repeat creates another. Does not write the letter file. |
| `note_list` | Write | Open mail notes this chair can see. | The first time the intended chair lists a note, writes an ack of shown. |
| `note_ack` | Write | Set the ack on a note this chair can see. | Writes that note. |
| `note_gate` | Write | Set the gate on a note. Nexus only. | Writes that note. |
| `note_remove` | Delete | Delete a note this chair authored. | Removes that note from the vault. A second call finds it already gone. |
| `now_view` | Read | Read the board. A nexus caller also gets sitreps, reconcile, and open mail. | Reads `NOW.md` and, for nexus, the vault. |

A tool add, remove, or rename updates this file and `CHANGELOG.md` in the same change.
