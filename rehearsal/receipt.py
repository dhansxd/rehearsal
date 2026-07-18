"""Portable, dependency-free validation for exported Rehearsal receipts."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
from pathlib import Path


ALGORITHM = "sha256"
CANONICALIZATION = "json-sort-keys-v1"
HEX_256 = re.compile(r"^[0-9a-f]{64}$")


class ReceiptVerificationError(ValueError):
    pass


def _canonical_bytes(receipt: dict) -> bytes:
    payload = {key: value for key, value in receipt.items() if key != "integrity"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def with_receipt_integrity(receipt: dict) -> dict:
    result = dict(receipt)
    result["integrity"] = {
        "algorithm": ALGORITHM,
        "canonicalization": CANONICALIZATION,
        "digest": hashlib.sha256(_canonical_bytes(result)).hexdigest(),
    }
    return result


def verify_receipt(receipt: dict) -> dict:
    if not isinstance(receipt, dict):
        raise ReceiptVerificationError("receipt must be a JSON object")
    integrity = receipt.get("integrity")
    if not isinstance(integrity, dict):
        raise ReceiptVerificationError("receipt integrity envelope is missing")
    if integrity.get("algorithm") != ALGORITHM or integrity.get("canonicalization") != CANONICALIZATION:
        raise ReceiptVerificationError("receipt integrity algorithm is unsupported")
    claimed = integrity.get("digest")
    actual = hashlib.sha256(_canonical_bytes(receipt)).hexdigest()
    if not isinstance(claimed, str) or not hmac.compare_digest(claimed, actual):
        raise ReceiptVerificationError("receipt integrity digest does not match its contents")

    required_digests = ("patch_digest", "base_state_digest", "observed_state_digest", "contract_digest")
    if any(not isinstance(receipt.get(name), str) or not HEX_256.fullmatch(receipt[name]) for name in required_digests):
        raise ReceiptVerificationError("receipt contains an invalid evidence digest")
    if receipt.get("verified") is not True or receipt.get("checks_passed") != receipt.get("checks_total"):
        raise ReceiptVerificationError("receipt does not prove a fully verified apply")
    rollback_verified = receipt.get("rollback_verified")
    rollback = receipt.get("rollback")
    if rollback_verified is True and rollback != "completed and verified":
        raise ReceiptVerificationError("rollback verification fields are inconsistent")
    if rollback_verified is not True and rollback != "available":
        raise ReceiptVerificationError("rollback state is unsupported")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a downloaded Rehearsal receipt JSON")
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    data = args.receipt.read_bytes()
    if len(data) > 1_000_000:
        raise SystemExit("FAIL: receipt exceeds 1 MB")
    try:
        verify_receipt(json.loads(data))
    except (json.JSONDecodeError, ReceiptVerificationError) as exc:
        raise SystemExit(f"FAIL: {exc}") from exc
    print("PASS: receipt contents and verification fields are internally consistent")


if __name__ == "__main__":
    main()
