"""Serve the local page on localhost. Reads only."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from envoy.paths import resolve_home, resolve_root
from envoy.view import board_snapshot, node_detail
from envoy.view_page import PAGE


def make_server(root: Path, home: Path, port: int) -> ThreadingHTTPServer:
    page = PAGE.encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if parsed.path in ("/", "/index.html"):
                self._bytes(200, "text/html; charset=utf-8", page)
                return
            if parsed.path == "/api/board":
                chair = (query.get("chair") or [""])[0] or None
                self._json(board_snapshot(root, home, chair))
                return
            if parsed.path == "/api/node":
                chair = (query.get("chair") or [""])[0]
                node = (query.get("node") or [""])[0]
                self._json(node_detail(root, home, chair, node))
                return
            self._bytes(404, "text/plain; charset=utf-8", b"not found")

        def _json(self, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self._bytes(200, "application/json; charset=utf-8", body)

        def _bytes(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(root: Path, home: Path, port: int = 4173) -> None:
    httpd = make_server(root, home, port)
    host, bound = httpd.server_address[:2]
    print(f"http://{host}:{bound}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


def view_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="envoy view", description="Local read-only page for the bulletin.")
    parser.add_argument("--root", default=None, help="Bulletin root. Or set ENVOY_ROOT.")
    parser.add_argument(
        "--vault",
        default=None,
        help="Record store when the bulletin root has no nexus.md. Or set ENVOY_HOME.",
    )
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args(argv)
    serve(resolve_root(cli_root=args.root), resolve_home(cli_vault=args.vault), args.port)
