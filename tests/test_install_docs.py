from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_install_reads_platforms_yaml() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    manual = (ROOT / "install" / "README.md").read_text(encoding="utf-8")
    block = (ROOT / "install" / "mcp.json.examples.md").read_text(encoding="utf-8")
    assert "platforms.yaml" in readme
    assert "platforms.yaml" in manual
    assert "ships no router" in manual.lower()
    assert "do not edit user-global" in manual.lower()
    for doc in (readme, manual, block):
        assert "~/.cursor/" not in doc
        assert "~/.claude" not in doc
        assert "~/.grok" not in doc
