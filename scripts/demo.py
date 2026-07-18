#!/usr/bin/env python3
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rehearsal.app import DemoController


with tempfile.TemporaryDirectory() as temporary:
    runtime = Path(temporary) / "runtime"
    demo = DemoController(runtime / "demo-workspace", demo_mode=True, approved_runtime_root=runtime)
    try:
        demo.reset()
        unsafe = demo.rehearse("remove unused project files")
        assert unsafe["stage"] == "unsafe"
        safe = demo.correct("Keep the public API example and make sure tests pass")
        assert safe["stage"] == "safe"
        applied = demo.approve(safe["preview"]["id"], safe["preview"]["patch_digest"])
        assert applied["receipt"]["verified"]
        rolled_back = demo.rollback()
        assert rolled_back["receipt"]["rollback"] == "completed and verified"
        print(json.dumps({
            "path": ["ready", "unsafe", "safe", "applied", "rolled_back"],
            "unsafe_deleted": unsafe["preview"]["deleted"],
            "safe_deleted": safe["preview"]["deleted"],
            "receipt": applied["receipt"]["id"],
            "patch_digest": applied["receipt"]["patch_digest"],
            "verified": True,
            "rollback": rolled_back["receipt"]["rollback"],
            "model_mode": safe["model_mode"],
        }, indent=2))
    finally:
        demo.close()
