import unittest
from pathlib import Path


class PublicExampleContract(unittest.TestCase):
    def test_documented_example_exists(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "examples/public_api.py").is_file())


if __name__ == "__main__":
    unittest.main()
