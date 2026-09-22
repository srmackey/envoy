# Security

## Reporting

Report a vulnerability privately with a GitHub Security Advisory on this repository. Do not open a public issue for a bug that would write outside the bulletin root and the vault, or expose another chair's mail.

## Trust boundary

- Transport is stdio. The host starts a local process as the user who launched it.
- Bulletin files live at `ENVOY_ROOT`. Map tools read and write `MAP.md` there. `now_view` reads `NOW.md`. The server reads a node's identity file and local status when a tool asks for them.
- Published sitreps and mail notes are JSON under `ENVOY_HOME`, or `~/.envoy` when that is unset.
- It does not write inbox letters.
- It does not use the network and it does not take a credential.
