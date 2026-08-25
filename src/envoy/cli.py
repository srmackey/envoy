from __future__ import annotations

import argparse
from pathlib import Path

from envoy.paths import resolve_home, resolve_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envoy",
        description="Envoy MCP server: the bulletin bulletin.",
    )
    parser.add_argument("--root", default=None, help="the bulletin root. Or set ENVOY_ROOT.")
    parser.add_argument("--vault", default=None, help="Vault root. Or set ENVOY_HOME. Default ~/.envoy.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    root = resolve_root(cli_root=args.root)
    home = resolve_home(cli_vault=args.vault)
    from envoy.server import run

    run(root=root, home=home)
