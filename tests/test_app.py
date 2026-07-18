import tempfile
import threading
import unittest
from pathlib import Path

from rehearsal.app import DemoController


class DemoControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        runtime = Path(self.temp.name) / "runtime"
        self.controller = DemoController(runtime / "demo-workspace", approved_runtime_root=runtime)

    def tearDown(self):
        self.controller.close()
        self.temp.cleanup()

    def test_complete_public_demo_flow(self):
        initial = self.controller.reset()
        self.assertEqual("ready", initial["stage"])

        unsafe = self.controller.rehearse("remove unused project files")
        self.assertEqual("unsafe", unsafe["stage"])
        self.assertFalse(unsafe["preview"]["tests"]["passed"])
        self.assertIn("examples/public_api.py", unsafe["preview"]["deleted"])

        safe = self.controller.correct("Keep the public API example and make sure tests pass")
        self.assertEqual("safe", safe["stage"])
        self.assertTrue(safe["preview"]["contract_proof"]["passed"])
        self.assertEqual("deterministic demo fallback", safe["model_mode"])

        applied = self.controller.approve(safe["preview"]["id"], safe["preview"]["patch_digest"])
        self.assertEqual("applied", applied["stage"])
        self.assertTrue(applied["receipt"]["verified"])

        rolled_back = self.controller.rollback()
        self.assertEqual("rolled_back", rolled_back["stage"])
        self.assertEqual("completed and verified", rolled_back["receipt"]["rollback"])

    def test_receipt_is_inspectable_and_links_one_transaction(self):
        self.controller.reset()
        self.controller.rehearse("remove unused project files")
        safe = self.controller.correct("Keep the public API example and make sure tests pass")
        applied = self.controller.approve(safe["preview"]["id"], safe["preview"]["patch_digest"])
        receipt = applied["receipt"]
        required = {
            "id", "transaction_id", "repository", "workspace", "branch",
            "base_head", "base_state_digest", "preview_id", "patch_digest",
            "contract_digest", "contract_revision", "generated_at", "approved_at",
            "model_mode", "explanation_mode", "checks_passed", "checks_total",
            "observed_state_digest", "rollback_class", "rollback_verified", "verified",
        }
        self.assertTrue(required <= set(receipt))
        self.assertEqual(safe["preview"]["transaction_id"], receipt["transaction_id"])
        self.assertEqual(safe["preview"]["contract_digest"], receipt["contract_digest"])
        self.assertEqual(64, len(receipt["patch_digest"]))
        self.assertEqual(64, len(receipt["base_state_digest"]))
        self.assertEqual(64, len(receipt["observed_state_digest"]))
        self.assertTrue(receipt["generated_at"].endswith("+00:00"))
        self.assertTrue(receipt["approved_at"].endswith("+00:00"))
        self.assertEqual(receipt["checks_total"], receipt["checks_passed"])
        self.assertFalse(receipt["rollback_verified"])
        rolled_back = self.controller.rollback()["receipt"]
        self.assertTrue(rolled_back["rollback_verified"])

    def test_approval_is_bound_to_current_preview_id_and_digest(self):
        self.controller.reset()
        first = self.controller.rehearse("remove unused project files")
        safe = self.controller.correct("Keep the public API example and make sure tests pass")
        stale_id = safe["preview"]["id"]
        stale_digest = safe["preview"]["patch_digest"]
        newer = self.controller.correct("Keep the public API example and make sure tests pass")
        with self.assertRaises(ValueError):
            self.controller.approve(stale_id, stale_digest)
        with self.assertRaises(ValueError):
            self.controller.approve(newer["preview"]["id"], "0" * 64)

    def test_model_explainer_receives_counts_and_booleans_not_repo_metadata(self):
        captured = {}
        self.controller.explainer.explain = lambda value: captured.update(value) or "safe summary"
        self.controller.reset()
        self.controller.rehearse("remove unused project files")
        serialized = str(captured)
        self.assertNotIn("public_api.py", serialized)
        self.assertNotIn("README.md", serialized)
        self.assertNotIn("FAILED", serialized)
        self.assertEqual(3, captured["deleted_count"])
        self.assertFalse(captured["tests_passed"])

    def test_mutations_are_serialized_across_approval_verification(self):
        self.controller.reset()
        self.controller.rehearse("remove unused project files")
        safe = self.controller.correct("Keep the public API example and make sure tests pass")
        entered, release, reset_done = threading.Event(), threading.Event(), threading.Event()
        original = self.controller.engine.approve

        def slow_approve(preview_id):
            entered.set()
            release.wait(2)
            return original(preview_id)

        self.controller.engine.approve = slow_approve
        approval = threading.Thread(target=lambda: self.controller.approve(safe["preview"]["id"], safe["preview"]["patch_digest"]))
        reset = threading.Thread(target=lambda: (self.controller.reset(), reset_done.set()))
        approval.start(); entered.wait(2); reset.start()
        self.assertFalse(reset_done.wait(.1))
        release.set(); approval.join(3); reset.join(3)
        self.assertTrue(reset_done.is_set())


if __name__ == "__main__":
    unittest.main()
