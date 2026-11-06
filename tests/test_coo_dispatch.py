"""COO dispatch idempotency and fail-closed checks."""
import json
import tempfile
import unittest
from pathlib import Path
from src.coo_dispatch import dispatch

class TestCooDispatch(unittest.TestCase):
    def test_once_per_day(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = dispatch(root, "20261106")
            second = dispatch(root, "20261106")
            self.assertEqual(len(first["created"]), 5)
            self.assertEqual(len(second["created"]), 0)
            self.assertEqual(len(second["existing"]), 5)
            for name in first["created"]:
                data = json.loads((root / "queue/pending" / (name + ".json")).read_text())
                self.assertEqual(data["origin"], "COO_DAILY_DISPATCH")
                self.assertEqual(data["state"], "PENDING")
            self.assertFalse(first["publication_authorized"])
    def test_invalid_day(self):
        with self.assertRaises(ValueError):
            dispatch(day="../../etc")

if __name__ == "__main__":
    unittest.main()
