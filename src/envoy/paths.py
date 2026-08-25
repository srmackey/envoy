from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


def resolve_root(
    *,
    env: Mapping[str, str] | None = None,
    cli_root: str | Path | None = None,
) -> Path:
    environ = os.environ if env is None else env
    value = str(environ.get("ENVOY_ROOT", "") or "").strip()
    if value:
        return Path(value).expanduser().resolve()
    if cli_root is not None and str(cli_root).strip():
        return Path(cli_root).expanduser().resolve()
    raise FileNotFoundError("ENVOY_ROOT or --root is required")


def resolve_home(
    *,
    env: Mapping[str, str] | None = None,
    cli_vault: str | Path | None = None,
    home: str | Path | None = None,
) -> Path:
    environ = os.environ if env is None else env
    value = str(environ.get("ENVOY_HOME", "") or "").strip()
    if value:
        return Path(value).expanduser().resolve()
    if cli_vault is not None and str(cli_vault).strip():
        return Path(cli_vault).expanduser().resolve()
    home_path = Path(home) if home is not None else Path.home()
    return (home_path / ".envoy").expanduser().resolve()
