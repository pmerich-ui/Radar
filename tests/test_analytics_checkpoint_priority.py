"""Regression: an already recorded video stays recorded if later API data is empty."""
import tempfile
import unittest
from pathlib import Path
from scripts.analytics_24h import record

class TestCheckpointPriority(unittest.TestCase):
    def test_recorded_checkpoint_precedes_missing_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "ledger.sqlite"
            args = ("video-123", "2026-11-10T18:00:00+01:00", "2026-11-12T06:00:00+01:00")
            first = record(db, *args, {"TKPO07": 0})
            self.assertEqual(first["status"], "RECORDED")
            again = record(db, *args, {})
            self.assertEqual(again["status"], "ALREADY_RECORDED")

if __name__ == "__main__":
    unittest.main()
