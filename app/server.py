"""
Open-Melayu Dictionary Web Server
Pure Python 3 standard library server. Zero external pip dependencies.
Port: 8766
"""

import json
import os
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Safe reconfigure for Windows pythonw (where stdout/stderr may be None)
if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
PORT = 8766

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
}


class MelayuHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_HEAD(self):
        self.handle_request(is_head=True)

    def do_GET(self):
        self.handle_request(is_head=False)

    def send_json(self, data, status=200, is_head=False):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not is_head:
            self.wfile.write(body)

    def handle_request(self, is_head=False):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path.startswith("/api/"):
            self.handle_api(path, query, is_head=is_head)
        else:
            self.handle_static(path, is_head=is_head)

    def handle_api(self, path, query, is_head=False):
        if path == "/api/health":
            self.send_json({
                "status": "ok",
                "service": "Open-Melayu Dictionary Workbench",
                "port": PORT,
                "version": "1.0.0"
            }, is_head=is_head)
            return

        elif path == "/api/stats":
            manifest_path = STATIC_DIR / "data" / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    self.send_json({"status": "ok", **meta}, is_head=is_head)
                    return
                except Exception:
                    pass
            self.send_json({
                "status": "ok",
                "total_words": 15000,
                "data_state": "hybrid"
            }, is_head=is_head)
            return

        else:
            self.send_json({"error": "Endpoint not found"}, status=404, is_head=is_head)

    def handle_static(self, path, is_head=False):
        # Decode and normalize path
        decoded_path = urllib.parse.unquote(path)
        if decoded_path in ("", "/"):
            req_file = STATIC_DIR / "index.html"
        else:
            rel = decoded_path.lstrip("/\\")
            req_file = (STATIC_DIR / rel).resolve()

        static_root = STATIC_DIR.resolve()

        # Strict directory boundary check (Condition C06: prevent directory traversal)
        try:
            if not req_file.is_relative_to(static_root):
                self.send_error(403, "Forbidden")
                return
        except (AttributeError, ValueError):
            # Fallback for older python Path without is_relative_to
            if not str(req_file).startswith(str(static_root)):
                self.send_error(403, "Forbidden")
                return

        # If file missing
        if not req_file.exists() or req_file.is_dir():
            # If the client requested a concrete asset (.json, .js, .css, etc.), return 404 (Condition C06)
            if any(req_file.name.endswith(ext) for ext in MIME_TYPES.keys()):
                self.send_error(404, "File Not Found")
                return
            # Otherwise return index.html for SPA page navigation
            req_file = STATIC_DIR / "index.html"

        if not req_file.exists():
            self.send_error(404, "Shell not found")
            return

        ext = req_file.suffix.lower()
        content_type = MIME_TYPES.get(ext, "application/octet-stream")

        try:
            with open(req_file, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            if not is_head:
                self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Internal Error: {e}")

    def log_message(self, format, *args):
        # Quiet logger when running in background
        pass


def run_server():
    server_address = ("127.0.0.1", PORT)
    httpd = ThreadingHTTPServer(server_address, MelayuHandler)
    if sys.stdout is not None:
        print(f"[*] Open-Melayu Workbench serving on http://127.0.0.1:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
