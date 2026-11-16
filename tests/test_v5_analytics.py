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


    def test_metadata_only_does_not_finalize(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshots.json"
            now = self.published + timedelta(days=2)
            self.assertFalse(record_once(path, "v1", self.published, now, {"TKPO02": "2026-11-15", "TKPO03": "https://example.com", "TKPO06": 18}))
            self.assertFalse(path.exists())

    def test_invalid_metrics_do_not_finalize_and_zero_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshots.json"
            now = self.published + timedelta(days=2)
            for value in (None, "", "  ", "N/A", "--", float("nan"), float("inf"), True):
                self.assertFalse(record_once(path, "v1", self.published, now, {"TKPO07": value}))
            self.assertFalse(path.exists())
            self.assertTrue(record_once(path, "v1", self.published, now, {"TKPO07": 0}))
            self.assertFalse(record_once(path, "v1", self.published, now, {"TKPO07": 1}))

if __name__ == "__main__":
    unittest.main()
