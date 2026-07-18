from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .contracts import OutcomeContract
from .receipt import with_receipt_integrity


class SafetyError(ValueError):
    pass


class ApprovalError(RuntimeError):
    pass


@dataclass
class TestResult:
    passed: bool
    summary: str


@dataclass
class ContractProof:
    passed: bool
    clauses: list[dict]
    violations: list[str]


@dataclass
class Preview:
    id: str
    contract: OutcomeContract
    added: list[str]
    changed: list[str]
    deleted: list[str]
    disk_delta: int
    broken_references: list[str]
    tests: TestResult
    contract_proof: ContractProof
    patch: str
    patch_digest: str
    base_hashes: dict[str, str]
    result_hashes: dict[str, str]
    base_head: str
    base_index_digest: str
    approval_generated_at: float
    approval_expires_at: float
    transaction_id: str
    contract_digest: str
    contract_revision: int
    generated_at: str
    explanation: str
    explanation_mode: str = "deterministic measured fallback"


@dataclass
class Receipt:
    id: str
    transaction_id: str
    repository: str
    workspace: str
    branch: str
    base_head: str
    base_state_digest: str
    preview_id: str
    patch_digest: str
    contract_digest: str
    contract_revision: int
    generated_at: str
    approved_at: str
    model_mode: str
    explanation_mode: str
    checks_passed: int
    checks_total: int
    observed_state_digest: str
    rollback_class: str
    rollback_verified: bool
    verified: bool
    file_hashes: dict[str, str]
    tests: TestResult
    contract_proof: ContractProof
    rollback: str


class RehearsalEngine:
    SAFE_INTENT = re.compile(r"^[\w\s.,'\-]+$")
    APPROVAL_TTL_SECONDS = 300

    def __init__(self, repo: Path, state_dir: Path | None = None, *, trusted_seed: bool = False):
        self.repo = Path(repo).resolve()
        self.state_dir = Path(state_dir or self.repo / ".rehearsal-state").resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.previews = {}
        self.receipts = {}
        self.worktrees = []
        self.active_preview_id = None
        self.used_preview_ids = set()
        self.transaction_id = uuid.uuid4().hex
        self.contract_revision = 0
        self.model_mode = "deterministic demo fallback"
        self.trusted_seed = trusted_seed
        self._git(self.repo, "rev-parse", "--show-toplevel")

    def close(self):
        for path in self.worktrees:
            self._git(self.repo, "worktree", "remove", "--force", str(path), check=False)
        self.worktrees.clear()

    def rehearse(self, intent: str, contract: OutcomeContract | None = None) -> Preview:
        if not self.trusted_seed:
            raise SafetyError("Automatic test execution is restricted to the trusted seed demo")
        self._validate_text(intent)
        contract = contract or OutcomeContract(intent=intent)
        self._validate_contract(contract)
        if self._git(self.repo, "status", "--porcelain"):
            raise SafetyError("Rehearsal requires a clean trusted demo workspace")
        base = self.snapshot(self.repo)
        base_head = self._git(self.repo, "rev-parse", "HEAD").strip()
        base_index = self._index_digest(self.repo)
        worktree = Path(tempfile.mkdtemp(prefix="rehearsal-", dir=self.state_dir))
        worktree.rmdir()
        self._git(self.repo, "worktree", "add", "--detach", str(worktree), "HEAD")
        self.worktrees.append(worktree)
        self._perform_cleanup(worktree, contract)
        status = self._status(worktree)
        patch = self._git(worktree, "diff", "--binary", "--no-ext-diff")
        result = self.snapshot(worktree)
        tests = self._run_tests(worktree)
        broken = self._broken_references(worktree, status["deleted"])
        proof = self._prove(contract, status, tests, broken, worktree, base)
        delta = self._size(result, worktree) - self._size(base, self.repo)
        preview_id = uuid.uuid4().hex[:12]
        generated_at = time.time()
        self.contract_revision += 1
        contract_digest = self._json_digest(contract.to_dict())
        digest = hashlib.sha256(patch.encode()).hexdigest()
        explanation = self._explain(status, tests, broken, proof, delta)
        preview = Preview(preview_id, contract, status["added"], status["changed"], status["deleted"], delta,
                          broken, tests, proof, patch, digest, base, result, base_head, base_index,
                          generated_at, generated_at + self.APPROVAL_TTL_SECONDS,
                          self.transaction_id, contract_digest, self.contract_revision,
                          self._timestamp(generated_at), explanation)
        self.previews[preview_id] = preview
        self.active_preview_id = preview_id
        return preview

    def approve(self, preview_id: str) -> Receipt:
        preview = self.previews.get(preview_id)
        if not preview:
            raise ApprovalError("Unknown preview")
        if preview_id in self.used_preview_ids:
            raise ApprovalError("Approval already used and cannot be replayed")
        if preview_id != self.active_preview_id:
            raise ApprovalError("Approval is obsolete because a newer preview exists")
        if time.time() > preview.approval_expires_at:
            raise ApprovalError("Approval expired; run a fresh rehearsal")
        if not preview.tests.passed or not preview.contract_proof.passed:
            raise ApprovalError("Approval blocked: tests and every contract clause must pass")
        if (self.snapshot(self.repo) != preview.base_hashes
                or self._git(self.repo, "rev-parse", "HEAD").strip() != preview.base_head
                or self._index_digest(self.repo) != preview.base_index_digest):
            raise ApprovalError("Preview is stale: the real workspace changed")
        self.used_preview_ids.add(preview_id)
        patch_file = self.state_dir / f"{preview.id}.patch"
        patch_file.write_text(preview.patch)
        try:
            self._git(self.repo, "apply", "--index", str(patch_file))
        except Exception as exc:
            if self._restore_base(preview):
                raise ApprovalError("Apply failed; original state was restored and verified") from exc
            raise ApprovalError("Apply failed; recovery failed and workspace state is uncertain") from exc
        actual_patch = self._git(self.repo, "diff", "--cached", "--binary", "--no-ext-diff")
        actual_hashes = self.snapshot(self.repo)
        tests = self._run_tests(self.repo)
        status = self._status(self.repo, cached=True)
        broken = self._broken_references(self.repo, status["deleted"])
        proof = self._prove(preview.contract, status, tests, broken, self.repo, preview.base_hashes)
        verified = (actual_hashes == preview.result_hashes and
                    hashlib.sha256(actual_patch.encode()).hexdigest() == preview.patch_digest and
                    tests.passed and proof.passed)
        if not verified:
            self._git(self.repo, "apply", "--reverse", "--index", str(patch_file), check=False)
            if not self._base_matches(preview) and not self._restore_base(preview):
                raise ApprovalError("Apply verification failed; recovery failed and workspace state is uncertain")
            raise ApprovalError("Apply verification failed; original state was restored and verified")
        receipt_id = uuid.uuid4().hex[:12]
        checks_total = len(proof.clauses)
        receipt = Receipt(
            id=receipt_id, transaction_id=preview.transaction_id,
            repository="bundled-trusted-demo", workspace=str(self.repo),
            branch=self._git(self.repo, "branch", "--show-current").strip() or "detached",
            base_head=preview.base_head, base_state_digest=self._json_digest(preview.base_hashes),
            preview_id=preview.id, patch_digest=preview.patch_digest,
            contract_digest=preview.contract_digest, contract_revision=preview.contract_revision,
            generated_at=preview.generated_at, approved_at=self._timestamp(),
            model_mode=self.model_mode, explanation_mode=preview.explanation_mode,
            checks_passed=sum(1 for clause in proof.clauses if clause["passed"]),
            checks_total=checks_total, observed_state_digest=self._json_digest(actual_hashes),
            rollback_class="verified reverse Git patch", rollback_verified=False,
            verified=True, file_hashes=actual_hashes, tests=tests,
            contract_proof=proof, rollback="available",
        )
        self.receipts[receipt_id] = (receipt, patch_file, preview.base_hashes)
        (self.state_dir / f"receipt-{receipt_id}.json").write_text(json.dumps(self.receipt_dict(receipt), indent=2))
        return receipt

    def rollback(self, receipt_id: str):
        item = self.receipts.get(receipt_id)
        if not item:
            raise ApprovalError("Unknown receipt")
        receipt, patch_file, original = item
        if self.snapshot(self.repo) != receipt.file_hashes:
            raise ApprovalError("Rollback blocked: workspace changed after apply")
        preview = self.previews[receipt.preview_id]
        try:
            self._git(self.repo, "apply", "--reverse", "--index", str(patch_file), check=False)
        except Exception as exc:
            if self._restore_applied(preview, patch_file, receipt):
                raise ApprovalError("Rollback failed; workspace remains applied and verified") from exc
            raise ApprovalError("Rollback failed; recovery failed and workspace state is uncertain") from exc
        if self.snapshot(self.repo) != original:
            if self._restore_applied(preview, patch_file, receipt):
                raise ApprovalError("Rollback failed; workspace remains applied and verified")
            raise ApprovalError("Rollback failed; recovery failed and workspace state is uncertain")
        receipt.rollback = "completed and verified"
        receipt.rollback_verified = True
        (self.state_dir / f"receipt-{receipt.id}.json").write_text(json.dumps(self.receipt_dict(receipt), indent=2))

    def _base_matches(self, preview):
        return (self.snapshot(self.repo) == preview.base_hashes
                and self._git(self.repo, "rev-parse", "HEAD").strip() == preview.base_head
                and self._index_digest(self.repo) == preview.base_index_digest)

    def _restore_base(self, preview):
        self._git(self.repo, "restore", "--source", preview.base_head, "--staged", "--worktree", "--", ".", check=False)
        for path in preview.added:
            target = self.repo / path
            if target.is_file() and not target.is_symlink():
                target.unlink()
        return self._base_matches(preview)

    def _restore_applied(self, preview, patch_file, receipt):
        if not self._restore_base(preview):
            return False
        self._git(self.repo, "apply", "--index", str(patch_file), check=False)
        actual_patch = self._git(self.repo, "diff", "--cached", "--binary", "--no-ext-diff")
        return (self.snapshot(self.repo) == receipt.file_hashes
                and hashlib.sha256(actual_patch.encode()).hexdigest() == receipt.patch_digest)

    def _index_digest(self, root):
        staged = self._git(root, "ls-files", "--stage")
        return hashlib.sha256(staged.encode()).hexdigest()

    @staticmethod
    def _json_digest(value):
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _timestamp(epoch=None):
        return datetime.fromtimestamp(epoch, timezone.utc).isoformat() if epoch is not None else datetime.now(timezone.utc).isoformat()

    def snapshot(self, root: Path):
        root = Path(root)
        result = {}
        for path in sorted(root.rglob("*")):
            if path.is_file() and ".git" not in path.relative_to(root).parts:
                rel = path.relative_to(root).as_posix()
                if (rel.startswith(".rehearsal-state/") or "__pycache__" in path.parts
                        or path.suffix in {".pyc", ".pyo"}):
                    continue
                result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        return result

    @staticmethod
    def receipt_dict(receipt):
        return with_receipt_integrity(asdict(receipt))

    def _perform_cleanup(self, root, contract):
        candidates = [Path("notes.tmp"), Path("scratch/old_benchmark.txt"), Path("examples/public_api.py")]
        preserve = set(contract.must_preserve)
        for relative in candidates:
            if relative.as_posix() in preserve:
                continue
            path = root / relative
            if path.is_file():
                path.unlink()
        scratch = root / "scratch"
        if scratch.exists() and not any(scratch.iterdir()):
            scratch.rmdir()

    def _status(self, root, cached=False):
        args = ["diff", "--name-status"]
        if cached:
            args.append("--cached")
        output = self._git(root, *args)
        result = {"added": [], "changed": [], "deleted": []}
        mapping = {"A": "added", "M": "changed", "D": "deleted"}
        for line in output.splitlines():
            if not line:
                continue
            code, path = line.split("\t", 1)
            result[mapping.get(code[0], "changed")].append(path)
        return result

    def _run_tests(self, root):
        process = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests"], cwd=root,
                                 text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
        lines = [line.strip() for line in process.stdout.splitlines() if line.strip()]
        summary = next((line for line in reversed(lines) if line.startswith(("OK", "FAILED"))), "no test summary")
        return TestResult(process.returncode == 0, summary)

    def _broken_references(self, root, deleted):
        broken = []
        deleted_set = set(deleted)
        link = re.compile(r"\[[^]]*\]\(([^)#]+)")
        for md in root.rglob("*.md"):
            if ".git" in md.parts:
                continue
            for target in link.findall(md.read_text(errors="replace")):
                resolved = (md.parent / target).resolve()
                try:
                    relative = resolved.relative_to(root.resolve()).as_posix()
                except ValueError:
                    continue
                if relative in deleted_set or not resolved.exists():
                    broken.append(md.relative_to(root).as_posix())
        return sorted(set(broken))

    def _prove(self, contract, status, tests, broken, root, base_hashes):
        clauses, violations = [], []
        changed = set(status["added"] + status["changed"] + status["deleted"])
        for path in contract.must_change:
            ok = path in changed
            clauses.append({"clause": f"must change {path}", "passed": ok, "evidence": "Git diff"})
            if not ok: violations.append(f"Required change absent: {path}")
        for path in contract.must_preserve:
            target = root / path
            actual_hash = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() and not target.is_symlink() else None
            ok = path not in changed and actual_hash is not None and actual_hash == base_hashes.get(path)
            clauses.append({"clause": f"preserve {path}", "passed": ok, "evidence": "SHA-256 identical to base" if ok else "content hash differs or file absent"})
            if not ok: violations.append(f"Protected file changed or absent: {path}")
        if "tests pass" in contract.proof:
            clauses.append({"clause": "tests pass", "passed": tests.passed, "evidence": tests.summary})
            if not tests.passed: violations.append("Test suite failed")
        if "no broken references" in contract.proof or "broken references" in contract.forbidden:
            ok = not broken
            clauses.append({"clause": "no broken references", "passed": ok,
                            "proof": "Markdown inline local-link scan",
                            "evidence": ", ".join(broken) or "reference scan clean"})
            violations.extend(f"Broken reference in {path}" for path in broken)
        return ContractProof(not violations, clauses, violations)

    @staticmethod
    def _explain(status, tests, broken, proof, delta):
        return (f"Measured candidate removes {len(status['deleted'])} file(s), changes disk use by {delta} bytes, "
                f"and leaves {len(broken)} broken documentation reference(s). Tests {'pass' if tests.passed else 'fail'}; "
                f"the contract {'passes' if proof.passed else 'is violated'}.")

    def _validate_text(self, text):
        if ".." in text or not self.SAFE_INTENT.fullmatch(text) or any(token in text for token in (";", "|", "`", "$", ">", "<")):
            raise SafetyError("Only a plain-language cleanup intent is accepted; paths and shell syntax are rejected")

    def _validate_contract(self, contract):
        for path in contract.must_change + contract.must_preserve:
            if not isinstance(path, str) or not path or "\\" in path or "\0" in path:
                raise SafetyError(f"Unsafe contract path: {path!r}")
            components = path.split("/")
            if any(part in {"", ".", ".."} for part in components):
                raise SafetyError(f"Ambiguous contract path: {path}")
            pure = PurePosixPath(path)
            if pure.is_absolute() or ".." in pure.parts or str(pure).startswith(".git"):
                raise SafetyError(f"Unsafe contract path: {path}")
            target = self.repo / path
            if target.is_symlink():
                raise SafetyError(f"Symlink contract path is forbidden: {path}")
            try:
                target.resolve().relative_to(self.repo)
            except ValueError as exc:
                raise SafetyError(f"Contract path escapes repository: {path}") from exc
        conflict = set(contract.must_change) & set(contract.must_preserve)
        if conflict:
            raise SafetyError(f"Contract path cannot be both change and preserve: {sorted(conflict)[0]}")

    @staticmethod
    def _size(snapshot, root):
        return sum((Path(root) / path).stat().st_size for path in snapshot)

    @staticmethod
    def _git(cwd, *args, check=True):
        process = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check and process.returncode:
            raise RuntimeError(process.stderr.strip())
        return process.stdout
