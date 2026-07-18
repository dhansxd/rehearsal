#!/usr/bin/env python3
"""Fail when tracked public claims drift from repository evidence."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SUBMISSION = ROOT / "docs" / "DEVPOST_SUBMISSION.md"
SESSION_ID = "019f7351-793e-7093-bc96-72e49183379b"
VIDEO_URL = "https://youtu.be/-yZ-59OqS2w"
REPOSITORY_URL = "https://github.com/dhansxd/rehearsal"
GALLERY = (
    ROOT / "docs" / "assets" / "rehearsal-safe-approval.png",
    ROOT / "docs" / "assets" / "rehearsal-verified-receipt.png",
)


def require(text: str, expected: str, source: Path) -> None:
    if expected not in text:
        raise AssertionError(f"{source.relative_to(ROOT)} missing: {expected}")


def png_evidence(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        raise AssertionError(f"{path.relative_to(ROOT)} is not a valid PNG")
    width, height = struct.unpack(">II", data[16:24])
    if width < 1000 or height < 600:
        raise AssertionError(f"{path.relative_to(ROOT)} is too small: {width}x{height}")
    return {
        "path": str(path.relative_to(ROOT)),
        "width": width,
        "height": height,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def main() -> None:
    readme = README.read_text(encoding="utf-8")
    submission = SUBMISSION.read_text(encoding="utf-8")
    sys.path.insert(0, str(ROOT))
    test_count = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), top_level_dir=str(ROOT)
    ).countTestCases()

    for text, source in ((readme, README), (submission, SUBMISSION)):
        require(text, SESSION_ID, source)
        require(text, VIDEO_URL, source)
        require(text, f"Ran {test_count} tests", source)
    require(submission, REPOSITORY_URL, SUBMISSION)
    require(submission, f"{test_count} automated", SUBMISSION)
    require(submission, f"{test_count} passing tests", SUBMISSION)

    assets = [png_evidence(path) for path in GALLERY]
    for asset in assets:
        require(readme, str(asset["path"]), README)

    print(json.dumps({
        "status": "PASS",
        "tests": test_count,
        "session_id": SESSION_ID,
        "video": VIDEO_URL,
        "repository": REPOSITORY_URL,
        "gallery": assets,
    }, indent=2))


if __name__ == "__main__":
    main()
