from pathlib import Path

import pytest

from envoy.paths import resolve_home, resolve_root


def test_resolve_root_from_env(tmp_path: Path) -> None:
    target = tmp_path / "dp"
    target.mkdir()
    got = resolve_root(env={"ENVOY_ROOT": str(target)}, cli_root=str(tmp_path / "other"))
    assert got == target.resolve()


def test_resolve_root_from_cli_when_env_empty(tmp_path: Path) -> None:
    target = tmp_path / "dp"
    target.mkdir()
    got = resolve_root(env={}, cli_root=target)
    assert got == target.resolve()


def test_resolve_root_missing_raises() -> None:
    with pytest.raises(FileNotFoundError):
        resolve_root(env={}, cli_root=None)


def test_resolve_home_prefers_env(tmp_path: Path) -> None:
    vault = tmp_path / "v"
    vault.mkdir()
    got = resolve_home(env={"ENVOY_HOME": str(vault)}, cli_vault=str(tmp_path / "x"))
    assert got == vault.resolve()


def test_resolve_home_default(tmp_path: Path) -> None:
    got = resolve_home(env={}, cli_vault=None, home=tmp_path)
    assert got == (tmp_path / ".envoy").resolve()
