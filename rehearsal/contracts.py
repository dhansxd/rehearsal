from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class OutcomeContract:
    intent: str
    must_change: list[str] = field(default_factory=list)
    must_preserve: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=lambda: ["broken references"])
    proof: list[str] = field(default_factory=lambda: ["tests pass", "no broken references"])
    rollback: str = "git checkpoint"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        keys = set(cls.__dataclass_fields__)
        if not isinstance(value, dict) or set(value) != keys:
            raise ValueError("Outcome Contract must contain exactly the required schema fields")
        return cls(**value)


class ContractCompiler:
    """Compile language at the semantic boundary; enforcement stays deterministic."""

    def __init__(self, demo_mode: bool | None = None):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.demo_mode = (not self.api_key) if demo_mode is None else demo_mode
        self.mode = "deterministic demo fallback" if self.demo_mode else "GPT-5.6"

    def compile(self, correction: str, current: OutcomeContract) -> OutcomeContract:
        if not correction.strip():
            raise ValueError("Correction cannot be empty")
        if self.demo_mode:
            candidate = self._fallback(correction, current)
        else:
            candidate = self._gpt(correction, current)
        return self._enforce(current, candidate)

    def _enforce(self, current: OutcomeContract, candidate: OutcomeContract) -> OutcomeContract:
        """Validate model output and make every constraint monotonic."""
        for name in ("intent", "rollback"):
            if not isinstance(getattr(candidate, name), str):
                raise ValueError(f"Contract {name} must be a string")
        if not candidate.intent or len(candidate.intent) > 500:
            raise ValueError("Contract intent must contain 1-500 characters")
        if candidate.rollback != "git checkpoint":
            raise ValueError("Unsupported rollback policy")
        fields = ("must_change", "must_preserve", "forbidden", "proof")
        for name in fields:
            value = getattr(candidate, name)
            if not isinstance(value, list) or len(value) > 100:
                raise ValueError(f"Contract {name} must be a list of at most 100 items")
            if any(not isinstance(item, str) or not item or len(item) > 256 for item in value):
                raise ValueError(f"Contract {name} contains an invalid item")
        supported_forbidden = {"broken references"}
        supported_proof = {"tests pass", "no broken references"}
        if not set(candidate.forbidden) <= supported_forbidden:
            raise ValueError("Contract contains an unsupported forbidden clause")
        if not set(candidate.proof) <= supported_proof:
            raise ValueError("Contract contains an unsupported proof clause")

        def union(old, new):
            return list(dict.fromkeys([*old, *new]))

        return OutcomeContract(
            intent=current.intent,
            must_change=union(current.must_change, candidate.must_change),
            must_preserve=union(current.must_preserve, candidate.must_preserve),
            forbidden=union(current.forbidden, candidate.forbidden),
            proof=union(current.proof, candidate.proof),
            rollback=current.rollback,
        )

    def _fallback(self, correction, current):
        lowered = correction.lower()
        preserve = list(current.must_preserve)
        if "public api" in lowered or "example" in lowered:
            if "examples/public_api.py" not in preserve:
                preserve.append("examples/public_api.py")
        proof = list(current.proof)
        if ("test" in lowered or "pass" in lowered) and "tests pass" not in proof:
            proof.append("tests pass")
        return OutcomeContract(
            intent=current.intent,
            must_change=list(current.must_change),
            must_preserve=preserve,
            forbidden=list(current.forbidden),
            proof=proof,
            rollback=current.rollback,
        )

    def _gpt(self, correction, current):
        schema = {
            "type": "object", "additionalProperties": False,
            "properties": {
                "intent": {"type": "string"},
                "must_change": {"type": "array", "items": {"type": "string"}},
                "must_preserve": {"type": "array", "items": {"type": "string"}},
                "forbidden": {"type": "array", "items": {"type": "string"}},
                "proof": {"type": "array", "items": {"type": "string"}},
                "rollback": {"type": "string"},
            },
            "required": ["intent", "must_change", "must_preserve", "forbidden", "proof", "rollback"],
        }
        body = {
            "model": "gpt-5.6",
            "input": [
                {"role": "system", "content": "Amend the supplied coding Outcome Contract. Preserve existing constraints. Paths must be repository-relative. Return only the schema."},
                {"role": "user", "content": json.dumps({"contract": current.to_dict(), "correction": correction})},
            ],
            "text": {"format": {"type": "json_schema", "name": "outcome_contract", "strict": True, "schema": schema}},
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.load(response)
            text = payload.get("output_text") or next(
                part["text"] for item in payload["output"] for part in item.get("content", []) if "text" in part
            )
            return OutcomeContract.from_dict(json.loads(text))
        except (urllib.error.URLError, KeyError, ValueError, StopIteration) as exc:
            raise RuntimeError(f"GPT-5.6 contract compilation failed: {exc}") from exc


class ConsequenceExplainer:
    def __init__(self, demo_mode: bool | None = None):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.demo_mode = (not self.api_key) if demo_mode is None else demo_mode
        self.mode = "deterministic measured fallback" if self.demo_mode else "GPT-5.6"

    def explain(self, measured: dict) -> str:
        if self.demo_mode:
            return measured["deterministic_summary"]
        body = {
            "model": "gpt-5.6",
            "instructions": "Explain only the supplied measured coding consequences in two concise sentences. Do not infer or invent facts.",
            "input": json.dumps(measured),
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses", data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.load(response)
            return payload["output_text"]
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            raise RuntimeError(f"GPT-5.6 consequence explanation failed: {exc}") from exc
