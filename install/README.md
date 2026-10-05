# Install

These files ship with the Envoy server, not inside a user's vault.

**Start the server.** Upsert the block in `install/mcp.json.examples.md` into each enabled host.

**Use the server.** This product ships no router. The use-instruction is the note the server returns when a host connects. Do not write a rules file.

The host list is `platforms.yaml`, next to `nexus.md`, in the folder `ENVOY_ROOT` names. This page does not name hosts or their files. The stored definition is that home.

## When there is no environment file

Do not edit user-global server config. Do not write a project instruction file.

Recording the host this agent is running in is how a machine gets its first `enabled` name. Look up that one host's server file, key, format, and where it loads user-global instructions. Write them into `platforms.yaml`. Set `enabled` to that one name. Do not search the profile for other hosts. Then run the pass below for that name only.

## Pass

Read `platforms.yaml`.

For each name in `enabled`:

- No stored definition: look up that host's real server file, key, format, and user-global instruction location. Write them under `platforms`. Do not paste paths from memory. Then continue.
- Server: for each `server` entry, open `path` and upsert the block under `key`, serialized as `format`. Leave every other key in that file alone.

Skip a definition you cannot apply, say which one, and continue with the other names.

Project-scoped `instructions` entries are not this product's. Leave them for the product that writes a project protocol.
