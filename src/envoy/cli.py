from __future__ import annotations

import argparse
import sys

from envoy.paths import resolve_home, resolve_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envoy",
        description="Envoy MCP server: bulletin (map, published status, mail notes).",
    )
    parser.add_argument("--root", default=None, help="Bulletin root. Or set ENVOY_ROOT.")
    parser.add_argument(
        "--vault",
        default=None,
        help="Record store when the bulletin root has no nexus.md. Or set ENVOY_HOME. Default ~/.envoy. When nexus.md is present, each nexus folder holds _envoy/.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "view":
        from envoy.view_server import view_main

        view_main(argv[1:])
        return
    args = build_parser().parse_args(argv)
    root = resolve_root(cli_root=args.root)
    home = resolve_home(cli_vault=args.vault)
    from envoy.server import run

    run(root=root, home=home)
