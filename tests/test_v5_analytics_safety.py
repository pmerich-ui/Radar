"""Regression tests for 24h snapshot crash safety and cross-timezone eligibility."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from src.v5_analytics import eligible, record_once


class AnalyticsSafetyRegressionTests(unittest.TestCase):
    def test_timezone_offsets_compare_same_instant(self):
        published = datetime(2026, 11, 15, 18, tzinfo=timezone.utc)
        swiss = timezone(timedelta(hours=1))
        before = datetime(2026, 11, 16, 18, 59, tzinfo=swiss)
        due = datetime(2026, 11, 16, 19, 0, tzinfo=swiss)
        self.assertFalse(eligible("public-1", published, before, {}))
        self.assertTrue(eligible("public-1", published, due, {}))

    def test_atomic_replace_failure_keeps_existing_snapshot(self):
        published = datetime(2026, 11, 14, 18, tzinfo=timezone.utc)
        captured = published + timedelta(days=2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "24h.json"
            original = {"old-video": {"metrics": {"views": 42}}}
            path.write_text(json.dumps(original), encoding="utf-8")
            with patch("src.v5_analytics.os.replace", side_effect=OSError("simulated disk failure")):
                with self.assertRaises(OSError):
                    record_once(path, "new-video", published, captured, {"views": 7})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), original)
            self.assertEqual(list(Path(directory).glob(".24h-*.tmp")), [])

    def test_missing_analytics_does_not_consume_snapshot(self):
        published = datetime(2026, 11, 14, 18, tzinfo=timezone.utc)
        captured = published + timedelta(days=2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "24h.json"
            self.assertFalse(record_once(path, "public-1", published, captured, {}))
            self.assertFalse(record_once(path, "public-1", published, captured, {"views": None, "reach": None}))
            self.assertFalse(record_once(path, "public-1", published, captured, {"views": "", "reach": "  "}))
            self.assertFalse(path.exists())
            self.assertTrue(record_once(path, "public-1", published, captured, {"views": 0}))
            self.assertEqual(json.loads(path.read_text())["public-1"]["metrics"]["views"], 0)

    def test_provider_placeholders_do_not_finalize_snapshot(self):
        published = datetime(2026, 11, 14, 18, tzinfo=timezone.utc)
        captured = published + timedelta(days=2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "24h.json"
            for invalid in ("N/A", "--", "null", True, float("nan"), float("inf")):
                self.assertFalse(record_once(path, "public-1", published, captured, {"TKPO07": invalid}))
            self.assertFalse(path.exists())
            self.assertTrue(record_once(path, "public-1", published, captured, {"TKPO07": "0"}))

    def test_repeated_capture_does_not_overwrite_first_snapshot(self):
        published = datetime(2026, 11, 14, 18, tzinfo=timezone.utc)
        captured = published + timedelta(days=2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "24h.json"
            self.assertTrue(record_once(path, "public-1", published, captured, {"views": 10}))
            self.assertFalse(record_once(path, "public-1", published, captured + timedelta(hours=1), {"views": 99}))
            self.assertEqual(json.loads(path.read_text())["public-1"]["metrics"]["views"], 10)


if __name__ == "__main__":
    unittest.main()
