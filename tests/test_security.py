import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rehearsal.app import DemoController, ROOT
from rehearsal.contracts import ContractCompiler, OutcomeContract
from rehearsal.engine import RehearsalEngine, SafetyError


class RuntimeRootSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_workspace_must_be_direct_safe_child_of_approved_runtime_root(self):
        runtime = self.base / "runtime"
        with self.assertRaises(SafetyError):
            DemoController(self.base / "outside" / "demo-workspace", approved_runtime_root=runtime)
        with self.assertRaises(SafetyError):
            DemoController(runtime / "nested" / "demo-workspace", approved_runtime_root=runtime)
        with self.assertRaises(SafetyError):
            DemoController(runtime / "other", approved_runtime_root=runtime)

    def test_runtime_and_workspace_reject_root_home_source_and_symlinks(self):
        for unsafe in (Path("/"), Path.home(), ROOT, ROOT / ".rehearsal-runtime"):
            with self.subTest(path=unsafe), self.assertRaises(SafetyError):
                DemoController(unsafe / "demo-workspace", approved_runtime_root=unsafe)
        runtime = self.base / "runtime"
        runtime.mkdir()
        target = self.base / "target"
        target.mkdir()
        linked = runtime / "demo-linked"
        linked.symlink_to(target, target_is_directory=True)
        with self.assertRaises(SafetyError):
            DemoController(linked, approved_runtime_root=runtime)

    def test_reset_removes_only_validated_workspace_not_runtime_siblings(self):
        runtime = self.base / "runtime"
        workspace = runtime / "demo-workspace"
        runtime.mkdir()
        sibling = runtime / "keep.txt"
        sibling.write_text("keep")
        controller = DemoController(workspace, approved_runtime_root=runtime)
        try:
            controller.reset()
            controller.reset()
            self.assertEqual("keep", sibling.read_text())
        finally:
            controller.close()


class ContractSecurityTests(unittest.TestCase):
    def test_contract_rejects_change_preserve_path_conflict(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            engine = RehearsalEngine.__new__(RehearsalEngine)
            engine.repo = repo.resolve()
            contract = OutcomeContract(
                intent="cleanup", must_change=["README.md"], must_preserve=["README.md"]
            )
            with self.assertRaisesRegex(SafetyError, "both change and preserve"):
                engine._validate_contract(contract)

    def test_unknown_fallback_correction_fails_explicitly(self):
        compiler = ContractCompiler(demo_mode=True)
        with self.assertRaisesRegex(ValueError, "could not map"):
            compiler.compile("Make it more enterprise", OutcomeContract(intent="cleanup"))

    def test_decoded_contract_requires_exact_schema(self):
        valid = OutcomeContract(intent="cleanup").to_dict()
        with self.assertRaises(ValueError):
            OutcomeContract.from_dict({**valid, "surprise": True})
        incomplete = dict(valid)
        incomplete.pop("proof")
        with self.assertRaises(ValueError):
            OutcomeContract.from_dict(incomplete)

    def test_model_contract_cannot_remove_or_weaken_existing_constraints(self):
        current = OutcomeContract(
            intent="cleanup", must_change=["notes.tmp"],
            must_preserve=["README.md"], forbidden=["broken references"],
            proof=["tests pass", "no broken references"],
        )
        weakened = OutcomeContract(intent="different", must_change=[], must_preserve=[], forbidden=[], proof=[])
        result = ContractCompiler(demo_mode=True)._enforce(current, weakened)
        self.assertEqual("cleanup", result.intent)
        self.assertIn("notes.tmp", result.must_change)
        self.assertIn("README.md", result.must_preserve)
        self.assertIn("broken references", result.forbidden)
        self.assertIn("tests pass", result.proof)

    def test_contract_schema_types_lengths_and_vocab_are_bounded(self):
        compiler = ContractCompiler(demo_mode=True)
        current = OutcomeContract(intent="cleanup")
        invalid = [
            OutcomeContract(intent="x" * 501),
            OutcomeContract(intent="cleanup", must_preserve="README.md"),
            OutcomeContract(intent="cleanup", must_preserve=["x" * 257]),
            OutcomeContract(intent="cleanup", proof=["model says looks fine"]),
            OutcomeContract(intent="cleanup", forbidden=["anything model dislikes"]),
        ]
        for contract in invalid:
            with self.subTest(contract=contract), self.assertRaises(ValueError):
                compiler._enforce(current, contract)

    def test_protected_paths_reject_ambiguous_and_symlink_forms(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            shutil.copytree(ROOT / "demo_seed", repo)
            os.symlink(repo / "README.md", repo / "readme-link")
            engine = RehearsalEngine.__new__(RehearsalEngine)
            engine.repo = repo.resolve()
            bad = ["foo\\bar", "foo/./bar", "foo//bar", "nul\0path", "readme-link", ".git/config", "../escape"]
            for value in bad:
                with self.subTest(path=value), self.assertRaises(SafetyError):
                    engine._validate_contract(OutcomeContract(intent="cleanup", must_preserve=[value]))

    def test_must_preserve_requires_identical_content_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "demo"
            shutil.copytree(ROOT / "demo_seed", repo)
            import subprocess
            for args in (("init", "-q"), ("config", "user.email", "demo@local"),
                         ("config", "user.name", "Demo"), ("add", "."), ("commit", "-qm", "seed")):
                subprocess.run(["git", *args], cwd=repo, check=True)
            engine = RehearsalEngine(repo, Path(temporary) / "state", trusted_seed=True)
            original_cleanup = engine._perform_cleanup
            def mutate(root, contract):
                original_cleanup(root, contract)
                (root / "README.md").write_text("silently replaced\n")
            try:
                with patch.object(engine, "_perform_cleanup", side_effect=mutate):
                    preview = engine.rehearse("cleanup", OutcomeContract(intent="cleanup", must_preserve=["README.md"]))
                self.assertFalse(preview.contract_proof.passed)
                self.assertTrue(any("README.md" in value for value in preview.contract_proof.violations))
            finally:
                engine.close()

    def test_untrusted_repository_test_execution_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "demo"
            shutil.copytree(ROOT / "demo_seed", repo)
            import subprocess
            for args in (("init", "-q"), ("config", "user.email", "demo@local"),
                         ("config", "user.name", "Demo"), ("add", "."), ("commit", "-qm", "seed")):
                subprocess.run(["git", *args], cwd=repo, check=True)
            engine = RehearsalEngine(repo, Path(temporary) / "state")
            try:
                with self.assertRaisesRegex(SafetyError, "trusted seed"):
                    engine.rehearse("cleanup")
            finally:
                engine.close()


if __name__ == "__main__":
    unittest.main()
