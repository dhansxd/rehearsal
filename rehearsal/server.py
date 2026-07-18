from __future__ import annotations

import argparse
import ipaddress
import json
import os
import secrets
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .app import DemoController, ROOT
from .engine import ApprovalError, SafetyError


def _header_values(headers, name):
    if hasattr(headers, "get_all"):
        return headers.get_all(name) or []
    value = headers.get(name)
    return [] if value is None else [value]


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
    host_values = _header_values(headers, "Host")
    if len(host_values) != 1:
        return False
    host_value = host_values[0]
    host = urlparse(f"//{host_value}")
    if not _loopback_name(host.hostname):
        return False
    if not require_origin:
        return True
    origin_values = _header_values(headers, "Origin")
    if len(origin_values) != 1:
        return False
    origin_value = origin_values[0]
    origin = urlparse(origin_value)
    if origin.scheme != "http" or not _loopback_name(origin.hostname):
        return False
    return origin.hostname.lower() == host.hostname.lower() and origin.port == host.port


class Handler(BaseHTTPRequestHandler):
    controller = None
    mutation_nonce = secrets.token_urlsafe(32)
    read_timeout_seconds = 5

    def do_GET(self):
        if not validate_local_request(self.headers):
            return self._json(403, {"error": "loopback Host required"})
        path = urlparse(self.path).path
        if path == "/api/state":
            state = self.controller.state()
            state["mutation_nonce"] = self.mutation_nonce
            return self._json(200, state)
        target = ROOT / "web" / ("index.html" if path == "/" else path.lstrip("/"))
        if not target.is_file() or (ROOT / "web") not in target.resolve().parents:
            return self._json(404, {"error": "not found"})
        mime = "text/css" if target.suffix == ".css" else "text/javascript" if target.suffix == ".js" else "text/html"
        data = target.read_bytes()
        self.send_response(200); self.send_header("Content-Type", mime); self.send_header("Cache-Control", "no-store"); self._security_headers(); self.send_header("Content-Length", len(data)); self.end_headers(); self.wfile.write(data)

    def do_POST(self):
        route = urlparse(self.path).path
        try:
            if not validate_local_request(self.headers, require_origin=True):
                return self._json(403, {"error": "same-origin loopback request required"})
            nonce_values = _header_values(self.headers, "X-Rehearsal-Nonce")
            if len(nonce_values) != 1 or not secrets.compare_digest(nonce_values[0], self.mutation_nonce):
                return self._json(403, {"error": "valid mutation nonce required"})
            if hasattr(self, "connection"):
                self.connection.settimeout(self.read_timeout_seconds)
            lengths = _header_values(self.headers, "Content-Length")
            if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
                raise ValueError("Content-Length must be one decimal value")
            size = int(lengths[0])
            if size > 16_384:
                raise ValueError("Request too large")
            body = json.loads(self.rfile.read(size) or b"{}")
            actions = {
                "/api/reset": lambda: self.controller.reset(),
                "/api/rehearse": lambda: self.controller.rehearse(body.get("intent", "")),
                "/api/correct": lambda: self.controller.correct(body.get("correction", "")),
                "/api/approve": lambda: self.controller.approve(body.get("preview_id"), body.get("patch_digest")),
                "/api/rollback": lambda: self.controller.rollback(),
            }
            if route not in actions: return self._json(404, {"error": "not found"})
            self._json(200, actions[route]())
        except (ApprovalError, SafetyError, ValueError) as exc:
            self._operation_error(400, route, str(exc))
        except Exception:
            self._operation_error(500, route, "Internal detail withheld")

    def _operation_error(self, status, route, detail):
        operation = route.removeprefix("/api/") or "request"
        changed = None if "uncertain" in detail.lower() else getattr(self.controller, "stage", None) == "applied"
        if operation == "rollback":
            message = "Rollback failed closed; restoration was not claimed."
        elif operation == "approve":
            message = "Apply and verification failed closed; no unverified outcome was accepted."
        else:
            message = "Operation failed closed; the last verified workspace state is authoritative."
        self._json(status, {
            "error": "Request rejected" if status < 500 else "Operation failed closed",
            "operation": operation,
            "workspace_changed": changed,
            "message": message,
            "detail": detail,
            "run_id": secrets.token_hex(6),
        })

    def _json(self, status, value):
        data = json.dumps(value).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json"); self._security_headers(); self.send_header("Content-Length", len(data)); self.end_headers(); self.wfile.write(data)

    def _security_headers(self):
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")

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
