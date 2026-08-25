from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / "bulletin"
    path.mkdir()
    return path


@pytest.fixture
def home(tmp_path: Path) -> Path:
    path = tmp_path / "envoy-home"
    path.mkdir()
    return path


def write_map(root: Path, entries: list[dict], updated: str = "2026-08-25") -> Path:
    path = root / "MAP.md"
    path.write_text(
        yaml.safe_dump({"updated": updated, "entries": entries}, sort_keys=False),
        encoding="utf-8",
    )
    return path


def write_project(folder: Path, data: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "project.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path
