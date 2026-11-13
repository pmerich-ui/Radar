"""Regression: a malformed Metricool row must not suppress valid 24h results."""
import tempfile
import unittest
from pathlib import Path
from scripts.tiktok_24h_snapshot import evaluate


class MalformedMetricoolRows(unittest.TestCase):
    def test_bad_date_does_not_abort_valid_video(self):
        with tempfile.TemporaryDirectory() as temp:
            state_path = str(Path(temp) / "state.json")
            good = {"url": "https://www.tiktok.com/@dealradar/video/7706032610681703702",
                    "published_at": "2026-11-09T05:02:21+01:00",
                    "duration": 6, "views": 0, "likes": 0}
            bad = dict(good, url="https://www.tiktok.com/@dealradar/video/7706032610681703703",
                       published_at="not-a-date")
            payload = {"now": "2026-11-13T20:43:00+01:00",
                       "state_path": state_path, "rows": [bad, good]}
            first = evaluate(payload)
            self.assertEqual(len(first), 1)
            self.assertEqual(first[0]["views"], 0)
            self.assertEqual(evaluate(payload), [])
            self.assertTrue(Path(state_path).exists())

    def test_missing_and_naive_dates_do_not_consume_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            payload = {"now": "2026-11-13T20:43:00+01:00",
                       "state_path": str(Path(temp) / "state.json"),
                       "rows": [
                           {"url": "https://www.tiktok.com/@dealradar/video/7706032610681703704", "views": 4},
                           {"url": "https://www.tiktok.com/@dealradar/video/7706032610681703705",
                            "published_at": "2026-11-09T05:02:21", "views": 5},
                           {"url": "https://www.tiktok.com/@dealradar/video/7706032610681703706",
                            "published_at": None, "views": 6},
                       ]}
            self.assertEqual(evaluate(payload), [])


if __name__ == "__main__":
    unittest.main()
