# Tools

Ten tools. Every call takes `chair`: `nexus`, or a name on the map.

The server does not set `readOnlyHint`, `destructiveHint`, `idempotentHint`, or `openWorldHint`. None of these tools use the network.

| Tool | What it does | Side effects |
|---|---|---|
| `map_list` | Read the roster. A nexus caller also sees each node's identity file when that file exists. | Reads `MAP.md`. |
| `map_upsert` | Create or replace one map row. Nexus only. | Writes `MAP.md`. |
| `status_put` | Publish this chair's sitrep. | Overwrites that chair's document in the vault. |
| `status_get` | Read a published sitrep. A node reads its own. Nexus reads children that opted in. | Reads the vault. |
| `note_post` | Create a mail note. The author is the calling chair. | Writes a note in the vault. Does not write the letter file. |
| `note_list` | Open mail notes this chair can see. | Reads the vault. |
| `note_ack` | Set the ack on a note this chair can see. | Writes that note. |
| `note_gate` | Set the gate on a note. Nexus only. | Writes that note. |
| `note_remove` | Delete a note this chair authored. | Removes that note from the vault. |
| `now_view` | Read the board. A nexus caller also gets sitreps, reconcile, and open mail. | Reads `NOW.md` and, for nexus, the vault. |

A tool add, remove, or rename updates this file and `CHANGELOG.md` in the same change.
