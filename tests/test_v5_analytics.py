import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from src.v5_analytics import eligible, record_once


class Analytics24hTests(unittest.TestCase):
    def setUp(self):
        self.published = datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc)

    def test_not_before_24_hours(self):
        self.assertFalse(eligible("v1", self.published, self.published + timedelta(hours=23, minutes=59), {}))

    def test_at_24_hours(self):
        self.assertTrue(eligible("v1", self.published, self.published + timedelta(hours=24), {}))

    def test_missing_public_id(self):
        self.assertFalse(eligible("", self.published, self.published + timedelta(days=2), {}))

    def test_timezone_required(self):
        with self.assertRaises(ValueError):
            eligible("v1", self.published.replace(tzinfo=None), self.published, {})

    def test_persistent_idempotency(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshots.json"
            now = self.published + timedelta(days=2)
            self.assertTrue(record_once(path, "v1", self.published, now, {"views": 15}))
            self.assertFalse(record_once(path, "v1", self.published, now, {"views": 20}))
            self.assertIn('"views": 15', path.read_text())
            self.assertNotIn('"views": 20', path.read_text())


if __name__ == "__main__":
    unittest.main()
