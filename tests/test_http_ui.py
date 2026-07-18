import io
import json
import unittest
from pathlib import Path

from rehearsal.server import Handler, validate_bind_host
from rehearsal.engine import SafetyError
from rehearsal.engine import ApprovalError


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


class FakeConnection:
    def __init__(self): self.timeout = None
    def settimeout(self, value): self.timeout = value


class MultiHeaders(dict):
    def __init__(self, values):
        super().__init__((key, entries[-1]) for key, entries in values.items())
        self.values = values
    def get_all(self, key): return self.values.get(key, [])


class CapturedHandler(Handler):
    def __init__(self, path, controller, body=None, host="127.0.0.1:8765", origin="http://127.0.0.1:8765", nonce="default"):
        self.path = path
        self.controller = controller
        encoded = json.dumps(body or {}).encode()
        self.headers = {"Content-Length": str(len(encoded)), "Host": host, "Origin": origin}
        if nonce is not None:
            self.headers["X-Rehearsal-Nonce"] = Handler.mutation_nonce if nonce == "default" else nonce
        self.rfile = io.BytesIO(encoded)
        self.connection = FakeConnection()
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
    def test_ui_contains_plain_language_state_and_structured_error_regions(self):
        html = (ROOT / "web/index.html").read_text()
        script = (ROOT / "web/app.js").read_text()
        self.assertIn('id="workspaceState"', html)
        self.assertIn('role="status"', html)
        self.assertIn('id="errorPanel"', html)
        self.assertIn('role="alert"', html)
        self.assertIn('id="errorTitle"', html)
        self.assertIn('tabindex="-1"', html)
        for text in (
            "Preview only — your project has not changed.",
            "Blocked — issues must be fixed.",
            "Ready for review — no changes applied yet.",
            "Applied — exact approved preview verified.",
            "Rollback complete — original state restored.",
        ):
            self.assertIn(text, script)
        self.assertIn("Approve deletion of", script)

    def test_ui_uses_persistent_errors_not_native_alerts(self):
        html = (ROOT / "web/index.html").read_text()
        script = (ROOT / "web/app.js").read_text()
        self.assertNotIn("alert(", script)
        for field in ("errorOperation", "errorWorkspace", "errorMessage", "errorDetail", "errorRunId"):
            self.assertIn(f'id="{field}"', html)
        for action in ("errorRetry", "errorReset", "errorRollback", "errorDismiss"):
            self.assertIn(f'id="{action}"', html)
        self.assertIn("focus()", script)

    def test_accessibility_and_narrow_layout_rules_are_present(self):
        html = (ROOT / "web/index.html").read_text()
        css = (ROOT / "web/style.css").read_text()
        self.assertIn('aria-busy="false"', html)
        self.assertIn(":focus-visible", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("min-height:44px", css)
        self.assertNotRegex(css, r"footer\{[^}]*position:fixed")
        self.assertIn("overflow-wrap:anywhere", css)

    def test_keyboard_correction_has_explicit_submit_focus_path(self):
        html = (ROOT / "web/index.html").read_text()
        script = (ROOT / "web/app.js").read_text()
        self.assertRegex(html, r'<form id="correction"[^>]*>')
        self.assertRegex(html, r'<button id="correct" type="submit" tabindex="0">')
        self.assertIn("$('correction').onsubmit = event =>", script)
        self.assertIn("event.preventDefault()", script)
        self.assertNotIn("$('correct').onclick", script)

    def test_inline_favicon_avoids_default_network_request(self):
        html = (ROOT / "web/index.html").read_text()
        self.assertRegex(html, r'<link rel="icon" href="data:image/svg\+xml,[^"]+">')
        self.assertNotIn('href="/favicon.ico"', html)
        handler = CapturedHandler("/", FakeController())
        handler.do_GET()
        self.assertIn("img-src 'self' data:", handler.response_headers["Content-Security-Policy"])

    def test_mobile_evidence_rows_preserve_status_and_compact_receipt(self):
        css = (ROOT / "web/style.css").read_text()
        self.assertIn(
            ".file span:first-child,.clause span:first-child{min-width:0;flex:1 1 auto;overflow-wrap:break-word;word-break:normal}",
            css,
        )
        self.assertIn(
            ".file span:last-child,.clause span:last-child{white-space:nowrap;flex:0 0 auto}",
            css,
        )
        self.assertIn(
            "@media(max-width:760px){.receipt-facts{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px 12px}",
            css,
        )

    def test_file_paths_use_escaped_separator_breaks(self):
        script = (ROOT / "web/app.js").read_text()
        self.assertIn("function pathHtml(value)", script)
        self.assertIn("String(value).split('/').map(esc).join('/<wbr>')", script)
        file_rows = script[script.index("function fileRows"):script.index("function render")]
        self.assertIn("${pathHtml(path)}", file_rows)
        self.assertNotIn("${esc(path)}", file_rows)

    def test_receipt_has_full_evidence_export_and_verification_help(self):
        html = (ROOT / "web/index.html").read_text()
        script = (ROOT / "web/app.js").read_text()
        self.assertIn('id="downloadReceipt"', html)
        self.assertIn('id="copyDigest"', html)
        self.assertIn('id="howVerified"', html)
        self.assertIn('href="#howVerified"', html)
        self.assertIn("application/json", script)
        self.assertIn("receipt.patch_digest", script)
        self.assertIn("receipt.integrity.digest", script)
        self.assertIn("Verify this export locally", html)
        self.assertIn("python3 -m rehearsal.receipt", html)

    def test_ui_exposes_accessible_measured_preview_comparison(self):
        html = (ROOT / "web/index.html").read_text()
        script = (ROOT / "web/app.js").read_text()
        self.assertIn('id="comparison"', html)
        self.assertIn('aria-labelledby="comparisonTitle"', html)
        for field in ("comparisonPrevented", "comparisonTests", "comparisonReferences", "comparisonContract",
                      "comparisonContractChanges"):
            self.assertIn(f'id="{field}"', html)
        for evidence in ("prevented_deletions", "tests_passed", "broken_references", "contract_passed",
                         "contract_added"):
            self.assertIn(evidence, script)
        self.assertNotIn("examples/public_api.py", script)

    def test_contract_delta_escapes_model_text_and_segments_paths(self):
        script = (ROOT / "web/app.js").read_text()
        self.assertIn("function contractDeltaHtml(contractAdded)", script)
        self.assertIn("pathHtml(value)", script)
        self.assertIn("esc(value)", script)
        self.assertNotIn("${value}", script[script.index("function contractDeltaHtml"):script.index("function render")])

    def test_ui_exposes_exact_state_binding_before_approval(self):
        html = (ROOT / "web/index.html").read_text()
        script = (ROOT / "web/app.js").read_text()
        self.assertIn('id="approvalBinding"', html)
        self.assertIn('aria-labelledby="approvalBindingTitle"', html)
        for field in ("bindingPreview", "bindingPatch", "bindingBase", "bindingContract"):
            self.assertIn(f'id="{field}"', html)
        for evidence in ("preview.id", "preview.patch_digest", "preview.base_index_digest",
                         "preview.contract_digest", "preview.contract_revision"):
            self.assertIn(evidence, script)
        self.assertIn("state.stage !== 'safe'", script)
        self.assertIn("navigator.clipboard.writeText(state.preview.patch_digest)", script)

    def test_contract_clauses_expose_escaped_deterministic_evidence(self):
        script = (ROOT / "web/app.js").read_text()
        css = (ROOT / "web/style.css").read_text()
        self.assertIn("clause.evidence", script)
        self.assertIn("clause.proof", script)
        self.assertIn("esc(evidence)", script)
        self.assertIn('class="clause-evidence"', script)
        self.assertIn(".clause-evidence{", css)
        self.assertIn("overflow-wrap:break-word", css)

    def test_long_operations_show_named_accessible_progress(self):
        html = (ROOT / "web/index.html").read_text()
        script = (ROOT / "web/app.js").read_text()
        self.assertIn('id="progressPanel"', html)
        self.assertIn('id="progressStage"', html)
        self.assertIn('role="status"', html)
        for stage in ("Candidate workspace", "Task execution", "Diff measured", "Tests", "Contract", "Review", "Apply", "Reverify", "Rollback"):
            self.assertIn(stage, html + script)
        self.assertIn("setTimeout", script)
        self.assertIn("500", script)

    def test_post_requires_process_mutation_nonce(self):
        for nonce in (None, "wrong"):
            handler = CapturedHandler("/api/approve", FakeController(),
                                      {"preview_id": "p1", "patch_digest": "d1"}, nonce=nonce)
            handler.do_POST()
            self.assertEqual(403, handler.status)

    def test_content_length_rejects_missing_invalid_negative_oversize_and_duplicate(self):
        invalid = [None, "-1", "+2", "abc", "16385"]
        for value in invalid:
            handler = CapturedHandler("/api/rollback", FakeController())
            if value is None: handler.headers.pop("Content-Length")
            else: handler.headers["Content-Length"] = value
            handler.do_POST()
            self.assertEqual(400, handler.status, value)
        handler = CapturedHandler("/api/rollback", FakeController())
        handler.headers = MultiHeaders({
            "Content-Length": ["2", "2"], "Host": ["127.0.0.1:8765"],
            "Origin": ["http://127.0.0.1:8765"],
            "X-Rehearsal-Nonce": [Handler.mutation_nonce],
        })
        handler.do_POST()
        self.assertEqual(400, handler.status)

    def test_http_sets_read_timeout_and_security_headers(self):
        handler = CapturedHandler("/api/rollback", FakeController())
        handler.do_POST()
        self.assertEqual(5, handler.connection.timeout)
        self.assertIn("default-src 'self'", handler.response_headers["Content-Security-Policy"])
        self.assertEqual("nosniff", handler.response_headers["X-Content-Type-Options"])
        self.assertEqual("DENY", handler.response_headers["X-Frame-Options"])

    def test_internal_exception_detail_is_not_returned(self):
        class Broken(FakeController):
            def rollback(self): raise RuntimeError("secret filesystem detail")
        handler = CapturedHandler("/api/rollback", Broken())
        handler.do_POST()
        body = handler.wfile.getvalue().decode()
        self.assertEqual(500, handler.status)
        self.assertNotIn("secret filesystem detail", body)
        self.assertIn("failed closed", body)

    def test_uncertain_recovery_never_claims_workspace_unchanged(self):
        class Uncertain(FakeController):
            stage = "safe"
            def approve(self, preview_id, patch_digest):
                raise ApprovalError("recovery failed and workspace state is uncertain")
        handler = CapturedHandler("/api/approve", Uncertain(), {"preview_id": "p1", "patch_digest": "d1"})
        handler.do_POST()
        payload = json.loads(handler.wfile.getvalue())
        self.assertIsNone(payload["workspace_changed"])
        script = (ROOT / "web/app.js").read_text()
        self.assertIn("Unknown — recovery could not prove workspace state.", script)

    def test_browser_bootstraps_and_sends_mutation_nonce(self):
        script = (ROOT / "web/app.js").read_text()
        self.assertIn("X-Rehearsal-Nonce", script)
        self.assertIn("fetch('/api/state'", script)

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
        self.assertLess(success_path.index("busy(false)"), success_path.index("render()"))

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
