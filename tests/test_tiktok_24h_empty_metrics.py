"""Regression: missing performance metrics must not consume a 24h checkpoint."""
import tempfile
import unittest
from pathlib import Path
from scripts.tiktok_24h_snapshot import evaluate

URL = "https://www.tiktok.com/@example/video/7706032610681703702"
PUBLISHED = "2026-11-09T05:02:21+01:00"
NOW = "2026-11-13T19:12:00+01:00"


class TestEmptyMetrics(unittest.TestCase):
    def test_empty_observation_is_retryable(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = str(Path(tmp) / "ledger.json")
            payload = {"now": NOW, "state_path": state,
                       "rows": [{"url": URL, "published_at": PUBLISHED,
                                 "views": None, "likes": None, "comments": None,
                                 "shares": None, "reach": None,
                                 "completion_rate": None,
                                 "average_watch_seconds": None}]}
            self.assertEqual(evaluate(payload), [])
            payload["rows"][0]["views"] = 0
            self.assertEqual(len(evaluate(payload)), 1)
            self.assertEqual(evaluate(payload), [])

    def test_zero_views_is_a_real_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = {"now": NOW, "state_path": str(Path(tmp) / "ledger.json"),
                       "rows": [{"url": URL, "published_at": PUBLISHED, "views": 0}]}
            recorded = evaluate(payload)
            self.assertEqual(len(recorded), 1)
            self.assertEqual(recorded[0]["decision"], "DATEN UNZUREICHEND")


if __name__ == "__main__":
    unittest.main()
