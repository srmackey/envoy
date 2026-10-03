"""A chair address opens that nexus's _envoy store and no other."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from envoy.mapfile import map_list
from envoy.notes_store import note_list, note_post
from envoy.status_store import status_get, status_put


def _nexus(folder: Path, name: str, rows: list[str], parent: str | None = None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    lines = [f"# nexus: {name}", ""]
    if parent:
        lines.extend([f"parent: {parent}", ""])
    lines.extend(
        [
            "| Node | Path | Kind | Status | Sensitive | Services | Triggers |",
            "|---|---|---|---|---|---|---|",
            *rows,
        ]
    )
    (folder / "nexus.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _project(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "project.yaml").write_text(
        yaml.safe_dump({"services": ["status", "mail"], "category": "node"}, sort_keys=False),
        encoding="utf-8",
    )


def _coast(tmp_path: Path) -> Path:
    root = tmp_path / "coast"
    _nexus(
        root,
        "coast",
        [
            "| harbor | harbor/ | nexus | active | no | status, mail | the inner harbor |",
            "| pier | pier/ | nexus | active | yes | status, mail | the far pier |",
            "| ledger | ledger/ | node | active | no | status | the tide ledger |",
        ],
    )
    _nexus(
        root / "harbor",
        "harbor",
        ["| dock | dock/ | node | active | no | status, mail | the harbor dock |"],
        parent="coast",
    )
    _nexus(
        root / "pier",
        "pier",
        [
            "| dock | dock/ | node | active | no | status, mail | the pier dock |",
            "| skiff | skiff/ | node | active | no | status, mail | the skiff |",
        ],
        parent="coast",
    )
    _project(root)
    _project(root / "harbor" / "dock")
    _project(root / "pier" / "dock")
    _project(root / "pier" / "skiff")
    return root


def _put(root: Path, home: Path, chair: str, forefront: str = "watch") -> dict:
    return status_put(root, home, chair, forefront, ["left"], ["next"], [])


def test_addressed_status_stays_in_that_nexus_store(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    result = _put(root, home, "harbor/dock", "harbor tide")
    assert result["ok"] is True
    assert result["document"]["node"] == "harbor/dock"

    harbor_file = root / "harbor" / "_envoy" / "status" / "dock.json"
    pier_file = root / "pier" / "_envoy" / "status" / "dock.json"
    assert harbor_file.is_file()
    assert json.loads(harbor_file.read_text(encoding="utf-8"))["forefront"] == "harbor tide"
    assert not pier_file.exists()
    assert not (home / "status" / "dock.json").exists()


def test_ambiguous_bare_name_is_unknown(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    result = _put(root, home, "dock")
    assert result == {"ok": False, "error": "unknown_chair"}


def test_unique_bare_name_and_root_alias(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    skiff = _put(root, home, "skiff", "one skiff")
    assert skiff["ok"] is True
    assert skiff["document"]["node"] == "pier/skiff"
    assert (root / "pier" / "_envoy" / "status" / "skiff.json").is_file()

    root_put = _put(root, home, "nexus", "the coast")
    assert root_put["ok"] is True
    assert root_put["document"]["node"] == "coast"
    record = root / "_envoy" / "status" / "coast.json"
    assert record.is_file()
    assert json.loads(record.read_text(encoding="utf-8"))["node"] == "coast"

    fetched = status_get(root, home, "nexus")
    assert fetched["ok"] is True
    assert fetched["document"]["forefront"] == "the coast"

    child = status_get(root, home, "harbor", node="pier/skiff")
    assert child["error"] == "forbidden"
    parent = status_get(root, home, "nexus", node="skiff")
    assert parent["ok"] is True
    assert parent["document"]["node"] == "pier/skiff"


def test_child_nexus_lists_its_own_nodes(tmp_path: Path) -> None:
    root = _coast(tmp_path)
    listed = map_list(root, "pier")
    assert listed["ok"] is True
    assert {item["name"] for item in listed["entries"]} == {"pier/dock", "pier/skiff"}

    refused = map_list(root, "coast/pier")
    assert refused["error"] == "unknown_chair"

    top = map_list(root, "nexus")
    names = {item["name"] for item in top["entries"]}
    assert "harbor" in names
    assert "pier" in names
    assert "coast/ledger" in names
    assert "coast/pier" not in names


def test_mail_is_written_to_both_nexus_stores(tmp_path: Path, home: Path) -> None:
    root = _coast(tmp_path)
    posted = note_post(root, home, "harbor/dock", "skiff", "inbox/tide.md", "the channel shifted")
    assert posted["ok"] is True
    note_id = posted["note"]["id"]
    assert posted["note"]["author"] == "harbor/dock"
    assert posted["note"]["intended_for"] == "pier/skiff"

    harbor_note = root / "harbor" / "_envoy" / "mail" / f"{note_id}.json"
    pier_note = root / "pier" / "_envoy" / "mail" / f"{note_id}.json"
    assert harbor_note.is_file()
    assert pier_note.is_file()
    assert not (root / "_envoy" / "mail" / f"{note_id}.json").exists()

    listed = note_list(root, home, "skiff")
    assert listed["ok"] is True
    assert [item["id"] for item in listed["notes"]] == [note_id]
