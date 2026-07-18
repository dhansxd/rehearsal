import copy
import json
import tempfile
import unittest
from pathlib import Path

from rehearsal.app import DemoController
from rehearsal.receipt import ReceiptVerificationError, verify_receipt


class PortableReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        runtime = Path(self.temp.name) / "runtime"
        self.controller = DemoController(runtime / "demo-workspace", approved_runtime_root=runtime)
        self.controller.reset()
        self.controller.rehearse("remove unused project files")
        safe = self.controller.correct("Keep the public API example and make sure tests pass")
        self.applied = self.controller.approve(safe["preview"]["id"], safe["preview"]["patch_digest"])

    def tearDown(self):
        self.controller.close()
        self.temp.cleanup()

    def test_exported_receipt_verifies_offline_and_tampering_fails_closed(self):
        receipt = self.applied["receipt"]
        self.assertEqual("sha256", receipt["integrity"]["algorithm"])
        self.assertEqual("json-sort-keys-v1", receipt["integrity"]["canonicalization"])
        self.assertEqual(receipt, verify_receipt(receipt))

        tampered = copy.deepcopy(receipt)
        tampered["checks_passed"] -= 1
        with self.assertRaisesRegex(ReceiptVerificationError, "integrity digest"):
            verify_receipt(tampered)

    def test_rolled_back_receipt_has_a_new_valid_integrity_digest(self):
        applied_digest = self.applied["receipt"]["integrity"]["digest"]
        rolled_back = self.controller.rollback()["receipt"]
        self.assertNotEqual(applied_digest, rolled_back["integrity"]["digest"])
        self.assertTrue(rolled_back["rollback_verified"])
        self.assertEqual(rolled_back, verify_receipt(json.loads(json.dumps(rolled_back))))


if __name__ == "__main__":
    unittest.main()
