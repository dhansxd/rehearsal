from __future__ import annotations

import json
import shutil
import subprocess
import threading
from dataclasses import asdict
from pathlib import Path

from .contracts import ConsequenceExplainer, ContractCompiler
from .engine import RehearsalEngine, SafetyError


ROOT = Path(__file__).resolve().parents[1]


class DemoController:
    def __init__(self, workspace: Path, demo_mode: bool | None = None, *, approved_runtime_root: Path):
        runtime_lexical = Path(approved_runtime_root).absolute()
        workspace_lexical = Path(workspace).absolute()
        forbidden = {Path("/").resolve(), Path.home().resolve(), ROOT.resolve()}
        if (runtime_lexical.is_symlink() or runtime_lexical.resolve() in forbidden
                or runtime_lexical.resolve().is_relative_to(ROOT.resolve())):
            raise SafetyError("Approved runtime root is unsafe")
        if workspace_lexical.parent != runtime_lexical or not workspace_lexical.name.startswith("demo-"):
            raise SafetyError("Workspace must be a direct demo-* child of the approved runtime root")
        if workspace_lexical.is_symlink():
            raise SafetyError("Workspace symlinks are forbidden")
        runtime_lexical.mkdir(parents=True, exist_ok=True)
        self.runtime_root = runtime_lexical.resolve()
        self.workspace = workspace_lexical.resolve()
        if self.workspace.parent != self.runtime_root or self.workspace in forbidden:
            raise SafetyError("Resolved workspace is outside the approved runtime root")
        self.compiler = ContractCompiler(demo_mode)
        self.explainer = ConsequenceExplainer(demo_mode)
        self.engine = None
        self.preview = None
        self.comparison = None
        self.receipt = None
        self.stage = "not_ready"
        self.lock = threading.RLock()

    def close(self):
        with self.lock:
            if self.engine:
                self.engine.close()

    def reset(self):
        with self.lock:
            self.close()
            self._assert_workspace_safe()
            if self.workspace.exists():
                shutil.rmtree(self.workspace)
            shutil.copytree(ROOT / "demo_seed", self.workspace)
            for args in (("init", "-q"), ("config", "user.email", "demo@rehearsal.local"),
                         ("config", "user.name", "Rehearsal Demo"), ("add", "."),
                         ("commit", "-qm", "seeded demo checkpoint")):
                subprocess.run(["git", *args], cwd=self.workspace, check=True)
            self.engine = RehearsalEngine(self.workspace, self.runtime_root / "engine-state", trusted_seed=True)
            self.engine.model_mode = self.compiler.mode
            self.preview = self.comparison = self.receipt = None
            self.stage = "ready"
            return self.state()

    def _assert_workspace_safe(self):
        if (self.workspace.is_symlink() or self.workspace.parent != self.runtime_root
                or not self.workspace.name.startswith("demo-") or self.workspace.resolve().parent != self.runtime_root):
            raise SafetyError("Workspace safety boundary changed")

    def rehearse(self, intent):
        with self.lock:
            if not self.engine:
                self.reset()
            self.comparison = None
            self.preview = self.engine.rehearse(intent)
            self._semantic_explanation()
            self.stage = "safe" if self.preview.contract_proof.passed else "unsafe"
            return self.state()

    def correct(self, correction):
        with self.lock:
            if not self.preview:
                raise ValueError("Run the first rehearsal before correcting it")
            before = self.preview
            contract = self.compiler.compile(correction, before.contract)
            self.preview = self.engine.rehearse(contract.intent, contract)
            self._semantic_explanation()
            self.comparison = self._compare_previews(before, self.preview)
            self.stage = "safe" if self.preview.contract_proof.passed else "unsafe"
            return self.state()

    def approve(self, preview_id, patch_digest):
        with self.lock:
            if not self.preview:
                raise ValueError("Nothing is ready for approval")
            if preview_id != self.preview.id or patch_digest != self.preview.patch_digest:
                raise ValueError("Approval is stale or does not match the displayed preview")
            self.receipt = self.engine.approve(self.preview.id)
            self.stage = "applied"
            return self.state()

    def rollback(self):
        with self.lock:
            if not self.receipt:
                raise ValueError("Nothing has been applied")
            self.engine.rollback(self.receipt.id)
            self.stage = "rolled_back"
            return self.state()

    def state(self):
        with self.lock:
            result = {"stage": self.stage, "model_mode": self.compiler.mode}
            if self.preview:
                preview = asdict(self.preview)
                preview["contract"] = self.preview.contract.to_dict()
                preview.pop("patch", None)
                result["preview"] = preview
            if self.comparison:
                result["comparison"] = self.comparison
            if self.receipt:
                result["receipt"] = self.engine.receipt_dict(self.receipt)
            return result

    @staticmethod
    def _compare_previews(before, after):
        before_deleted = set(before.deleted)
        after_deleted = set(after.deleted)
        contract_fields = ("must_change", "must_preserve", "forbidden", "proof")
        return {
            "from_preview_id": before.id,
            "to_preview_id": after.id,
            "prevented_deletions": sorted(before_deleted - after_deleted),
            "new_deletions": sorted(after_deleted - before_deleted),
            "tests_passed": {"before": before.tests.passed, "after": after.tests.passed},
            "broken_references": {
                "before": len(before.broken_references), "after": len(after.broken_references),
            },
            "contract_passed": {
                "before": before.contract_proof.passed, "after": after.contract_proof.passed,
            },
            "contract_added": {
                field: [value for value in getattr(after.contract, field)
                        if value not in getattr(before.contract, field)]
                for field in contract_fields
            },
        }

    def _semantic_explanation(self):
        p = self.preview
        p.explanation = self.explainer.explain({
            "deleted_count": len(p.deleted), "changed_count": len(p.changed),
            "disk_delta_bytes": p.disk_delta, "broken_reference_count": len(p.broken_references),
            "tests_passed": p.tests.passed, "contract_passed": p.contract_proof.passed,
            "violation_count": len(p.contract_proof.violations),
            "deterministic_summary": p.explanation,
        })
        p.explanation_mode = self.explainer.mode
