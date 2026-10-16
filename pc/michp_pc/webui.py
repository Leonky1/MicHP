"""PC software UI: local web server (127.0.0.1 only) + the pages in static/."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

_BASE = getattr(sys, "_MEIPASS", None)
if _BASE:  # running from the PyInstaller .exe
    STATIC_DIR = os.path.join(_BASE, "michp_pc", "static")
else:
    STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
}


class App:
    """Glue between the UI, PcCore and AudioOutput."""

    def __init__(self, core, audio):
        self.core = core
        self.audio = audio

    def state(self):
        snap = self.core.snapshot()
        snap["gain_percent"] = int(round(self.core.gain * 50))  # 50% = original volume
        snap["audio"] = self.audio.info()
        return snap


def make_server(app, port=8765, host="127.0.0.1"):
    class Handler(BaseHTTPRequestHandler):
        server_version = "MicHP"

        def log_message(self, *args):
            pass

        # --- security: other web pages must not be able to control this local API ---
        def _port(self):
            return self.server.server_address[1]

        def _host_ok(self):
            h = (self.headers.get("Host") or "").lower()
            return h in ("127.0.0.1:%d" % self._port(), "localhost:%d" % self._port())

        def _origin_ok(self):
            o = self.headers.get("Origin")
            return o is None or o in ("http://127.0.0.1:%d" % self._port(),
                                      "http://localhost:%d" % self._port())

        def _json(self, obj, status=200):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self._host_ok():
                return self._json({"error": "host"}, 403)
            path = urlparse(self.path).path
            if path == "/api/state":
                return self._json(app.state())
            if path == "/":
                path = "/index.html"
            name = os.path.basename(path)
            full = os.path.join(STATIC_DIR, name)
            ext = os.path.splitext(name)[1]
            if name.startswith(".") or ext not in MIME or not os.path.isfile(full):
                return self._json({"error": "not found"}, 404)
            with open(full, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", MIME[ext])
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if not (self._host_ok() and self._origin_ok()
                    and self.headers.get("X-MicHP") == "1"):
                return self._json({"error": "forbidden"}, 403)
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return self._json({"error": "bad length"}, 400)
            if length > 4096:
                return self._json({"error": "too large"}, 413)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError
            except ValueError:
                return self._json({"error": "bad json"}, 400)

            path = urlparse(self.path).path
            ok = True
            if path == "/api/connect":
                ok = app.core.connect(str(body.get("id", "")))
            elif path == "/api/disconnect":
                app.core.disconnect()
            elif path == "/api/gain":
                try:
                    pct = max(0.0, min(100.0, float(body.get("percent"))))
                except (TypeError, ValueError):
                    return self._json({"error": "bad percent"}, 400)
                app.core.set_gain(pct / 50.0)
            elif path == "/api/monitor":
                ok = app.audio.set_monitor(bool(body.get("on")))
            elif path == "/api/output":
                idx = body.get("index")
                if idx is not None and not isinstance(idx, int):
                    return self._json({"error": "bad index"}, 400)
                ok = app.audio.select_virtual(idx)
            else:
                return self._json({"error": "not found"}, 404)
            self._json({"ok": bool(ok), "state": app.state()})

    class Server(ThreadingHTTPServer):
        daemon_threads = True

    return Server((host, port), Handler)
