# Server block

Envoy needs a bulletin root and a vault. Set `ENVOY_ROOT` (required) and `ENVOY_HOME` (default `~/.envoy` on POSIX, or pass `--vault`).

When `ENVOY_ROOT` contains `nexus.md`, that file is the roster and each nexus folder holds `_envoy/`. `platforms.yaml` sits next to that file. `ENVOY_HOME` is the record store only when `nexus.md` is absent.

`ENVOY_ROOT` and `ENVOY_HOME` win over `--root` and `--vault` when both are set. On POSIX, a typical vault is `~/.envoy` (expand `~` to an absolute path if the host does not).

Where this block is written is `install/README.md`. The host file, the format, and the key come from `platforms.yaml`. This page does not name them.

Replace the paths with your checkout and bulletin root.

```yaml
command: uv
args:
  - run
  - --directory
  - /path/to/envoy
  - envoy
env:
  ENVOY_ROOT: /path/to/bulletin
  ENVOY_HOME: /path/to/envoy-vault
```

When `format` is `json`, write that as an object under the definition's `key`. When `format` is `toml`, write it as a table under that key.
