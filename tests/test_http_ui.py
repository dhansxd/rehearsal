import io
import json
import unittest
from pathlib import Path

from rehearsal.server import Handler, validate_bind_host
from rehearsal.engine import SafetyError


ROOT = Path(__file__).resolve().parents[1]


class FakeController:
    def __init__(self):
        self.calls = []

    def approve(self, preview_id, patch_digest):
        self.calls.append(("approve", preview_id, patch_digest))
        return {"stage": "applied", "receipt": {"verified": True}}

    def rollback(self):
        self.calls.append("rollback")
        return {"stage": "rolled_back", "receipt": {"rollback": "completed and verified"}}


class CapturedHandler(Handler):
    def __init__(self, path, controller, body=None, host="127.0.0.1:8765", origin="http://127.0.0.1:8765"):
        self.path = path
        self.controller = controller
        encoded = json.dumps(body or {}).encode()
        self.headers = {"Content-Length": str(len(encoded)), "Host": host, "Origin": origin}
        self.rfile = io.BytesIO(encoded)
        self.status = None
        self.response_headers = {}
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.response_headers[name] = value

    def end_headers(self):
        pass


class BrowserRegressionTests(unittest.TestCase):
    def test_server_bind_is_loopback_only(self):
        for host in ("127.0.0.1", "localhost", "::1"):
            self.assertIsNone(validate_bind_host(host))
        for host in ("0.0.0.0", "::", "192.168.1.10", "example.com"):
            with self.assertRaises(ValueError):
                validate_bind_host(host)

    def test_cross_site_and_non_loopback_host_posts_fail_closed(self):
        for host, origin in (("evil.example", "http://evil.example"),
                             ("127.0.0.1:8765", "https://evil.example"),
                             ("127.0.0.1:8765", "null")):
            controller = FakeController()
            handler = CapturedHandler("/api/approve", controller, host=host, origin=origin)
            handler.do_POST()
            self.assertEqual(403, handler.status)
            self.assertEqual([], controller.calls)

    def test_html_uses_versioned_static_asset_urls(self):
        html = (ROOT / "web/index.html").read_text()
        self.assertRegex(html, r'href="/style\.css\?v=[^"]+"')
        self.assertRegex(html, r'src="/app\.js\?v=[^"]+"')

    def test_static_assets_are_served_no_store(self):
        controller = FakeController()
        handler = CapturedHandler("/app.js?v=approval-cache-fix", controller)
        handler.do_GET()
        self.assertEqual(200, handler.status)
        self.assertEqual("no-store", handler.response_headers.get("Cache-Control"))

    def test_buttons_are_reenabled_before_safe_state_is_rendered(self):
        """A visible approve button must already be actionable."""
        script = (ROOT / "web/app.js").read_text()
        success_path = script[script.index("async function post"):script.index("function busy")]
        self.assertIn("state=data;busy(false);render()", success_path)

    def test_http_approve_route_calls_controller_and_returns_receipt(self):
        controller = FakeController()
        handler = CapturedHandler("/api/approve", controller, {"preview_id": "p1", "patch_digest": "d1"})
        handler.do_POST()
        self.assertEqual(200, handler.status)
        self.assertEqual([("approve", "p1", "d1")], controller.calls)
        self.assertTrue(json.loads(handler.wfile.getvalue())["receipt"]["verified"])

    def test_http_rollback_route_calls_controller_and_returns_verification(self):
        controller = FakeController()
        handler = CapturedHandler("/api/rollback", controller)
        handler.do_POST()
        self.assertEqual(200, handler.status)
        self.assertEqual(["rollback"], controller.calls)
        self.assertEqual("completed and verified", json.loads(handler.wfile.getvalue())["receipt"]["rollback"])


if __name__ == "__main__":
    unittest.main()
