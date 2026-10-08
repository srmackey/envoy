"""Serve the local page on localhost. Reads only."""

from __future__ import annotations

import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from envoy.paths import resolve_home, resolve_root
from envoy.view import snapshot

PORT = 4173
RETRY_SECONDS = 30.0

_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
}


def load_assets() -> dict[str, tuple[str, bytes]]:
    """Every page file shipped in the package, keyed by URL path.

    Only these paths are served, so a request can never reach outside the page.
    """
    web = files("envoy") / "web"
    assets: dict[str, tuple[str, bytes]] = {}

    def walk(folder, prefix: str) -> None:
        for item in folder.iterdir():
            if item.is_dir():
                walk(item, f"{prefix}{item.name}/")
                continue
            kind = _TYPES.get(Path(item.name).suffix)
            if kind:
                assets[f"/{prefix}{item.name}"] = (kind, item.read_bytes())

    walk(web, "")
    assets["/"] = assets["/index.html"]
    return assets


def make_server(root: Path, home: Path, port: int) -> ThreadingHTTPServer:
    assets = load_assets()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if parsed.path == "/api/snapshot":
                chair = (query.get("chair") or [""])[0] or None
                since = (query.get("since") or [""])[0] or None
                self._json(snapshot(root, home, chair, since=since))
                return
            asset = assets.get(parsed.path)
            if asset is None:
                self._bytes(404, "text/plain; charset=utf-8", b"not found")
                return
            self._bytes(200, *asset)

        def _json(self, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self._bytes(200, "application/json; charset=utf-8", body)

        def _bytes(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    return _Server(("127.0.0.1", port), Handler)


class _Server(ThreadingHTTPServer):
    # On Windows, address reuse lets a second server bind a port that is
    # already serving, and the browser keeps reaching the first one.
    allow_reuse_address = os.name != "nt"


def page_port() -> int:
    raw = os.environ.get("ENVOY_VIEW_PORT", "").strip()
    return int(raw) if raw.isdigit() else PORT


def page_enabled() -> bool:
    return os.environ.get("ENVOY_VIEW", "").strip().casefold() not in {"0", "off", "false", "no"}


def keep_page_up(
    root: Path,
    home: Path,
    *,
    port: int | None = None,
    retry: float = RETRY_SECONDS,
    stop: threading.Event | None = None,
) -> threading.Thread | None:
    """Serve the page from this process while no other process does.

    Every Envoy a host starts calls this. The first to bind the port serves it, and
    the rest try again every `retry` seconds, so the page comes back when the one
    serving exits. Nothing is written to stdout, which carries the MCP protocol.
    """
    if not page_enabled():
        return None
    stop = stop or threading.Event()
    port = page_port() if port is None else port

    def loop() -> None:
        while not stop.is_set():
            try:
                httpd = make_server(root, home, port)
            except OSError:
                stop.wait(retry)
                continue
            threading.Thread(target=lambda: (stop.wait(), httpd.shutdown()), daemon=True).start()
            try:
                httpd.serve_forever()
            finally:
                httpd.server_close()
            return

    thread = threading.Thread(target=loop, name="envoy-page", daemon=True)
    thread.start()
    return thread


def serve(root: Path, home: Path, port: int = PORT) -> None:
    try:
        httpd = make_server(root, home, port)
    except OSError:
        raise SystemExit(f"Port {port} is in use. Envoy may already be serving the page there. Pick another with --port.")
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
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args(argv)
    serve(resolve_root(cli_root=args.root), resolve_home(cli_vault=args.vault), args.port)
