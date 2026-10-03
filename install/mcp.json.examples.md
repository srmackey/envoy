# MCP host snippets

Envoy needs a bulletin root and a vault. Set `ENVOY_ROOT` (required) and `ENVOY_HOME` (default `~/.envoy` on POSIX, or pass `--vault`).

When `ENVOY_ROOT` contains `nexus.md`, that file is the roster and each nexus folder holds `_envoy/`. `ENVOY_HOME` is the record store only when `nexus.md` is absent.

Replace the paths below with your checkout and bulletin root.

## Cursor (`~/.cursor/mcp.json` or project `.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "envoy": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/envoy",
        "envoy"
      ],
      "env": {
        "ENVOY_ROOT": "/path/to/bulletin",
        "ENVOY_HOME": "/path/to/envoy-vault"
      }
    }
  }
}
```

## Claude Code (`~/.claude.json` mcpServers, or a project `.mcp.json`)

```json
{
  "mcpServers": {
    "envoy": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/envoy",
        "envoy"
      ],
      "env": {
        "ENVOY_ROOT": "/path/to/bulletin",
        "ENVOY_HOME": "/path/to/envoy-vault"
      }
    }
  }
}
```

## Grok (`~/.grok/config.toml`)

```toml
[mcp_servers.envoy]
command = "uv"
args = ["run", "--directory", "/path/to/envoy", "envoy"]

[mcp_servers.envoy.env]
ENVOY_ROOT = "/path/to/bulletin"
ENVOY_HOME = "/path/to/envoy-vault"
```

`ENVOY_ROOT` / `ENVOY_HOME` win over `--root` / `--vault` when both are set. On POSIX, a typical vault is `~/.envoy` (expand to an absolute path in JSON if the host does not expand `~`).
