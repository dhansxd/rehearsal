from __future__ import annotations

import argparse
import ipaddress
import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .app import DemoController, ROOT


def _loopback_name(hostname):
    if not hostname:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def validate_bind_host(host):
    if not _loopback_name(host):
        raise ValueError("Rehearsal may bind only to a loopback address")


def validate_local_request(headers, require_origin=False):
    host_value = headers.get("Host", "")
    host = urlparse(f"//{host_value}")
    if not _loopback_name(host.hostname):
        return False
    if not require_origin:
        return True
    origin_value = headers.get("Origin", "")
    origin = urlparse(origin_value)
    if origin.scheme != "http" or not _loopback_name(origin.hostname):
        return False
    return origin.hostname.lower() == host.hostname.lower() and origin.port == host.port


class Handler(BaseHTTPRequestHandler):
    controller = None

    def do_GET(self):
        if not validate_local_request(self.headers):
            return self._json(403, {"error": "loopback Host required"})
        path = urlparse(self.path).path
        if path == "/api/state":
            return self._json(200, self.controller.state())
        target = ROOT / "web" / ("index.html" if path == "/" else path.lstrip("/"))
        if not target.is_file() or (ROOT / "web") not in target.resolve().parents:
            return self._json(404, {"error": "not found"})
        mime = "text/css" if target.suffix == ".css" else "text/javascript" if target.suffix == ".js" else "text/html"
        data = target.read_bytes()
        self.send_response(200); self.send_header("Content-Type", mime); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", len(data)); self.end_headers(); self.wfile.write(data)

    def do_POST(self):
        try:
            if not validate_local_request(self.headers, require_origin=True):
                return self._json(403, {"error": "same-origin loopback request required"})
            size = int(self.headers.get("Content-Length", "0"))
            if size > 16_384: raise ValueError("Request too large")
            body = json.loads(self.rfile.read(size) or b"{}")
            route = urlparse(self.path).path
            actions = {
                "/api/reset": lambda: self.controller.reset(),
                "/api/rehearse": lambda: self.controller.rehearse(body.get("intent", "")),
                "/api/correct": lambda: self.controller.correct(body.get("correction", "")),
                "/api/approve": lambda: self.controller.approve(body.get("preview_id"), body.get("patch_digest")),
                "/api/rollback": lambda: self.controller.rollback(),
            }
            if route not in actions: return self._json(404, {"error": "not found"})
            self._json(200, actions[route]())
        except Exception as exc:
            self._json(400, {"error": str(exc)})

    def _json(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", len(data)); self.end_headers(); self.wfile.write(data)

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="Run the Rehearsal demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--runtime-root", type=Path, default=Path(tempfile.gettempdir()) / f"rehearsal-agent-runtime-{os.getuid()}")
    args = parser.parse_args()
    validate_bind_host(args.host)
    Handler.controller = DemoController(args.runtime_root / "demo-workspace", approved_runtime_root=args.runtime_root)
    Handler.controller.reset()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Rehearsal ready at http://{args.host}:{args.port} ({Handler.controller.compiler.mode})", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: Handler.controller.close(); server.server_close()


if __name__ == "__main__":
    main()
