"""Regression tests for the fail-closed TikTok snapshot evaluator."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tiktok_24h_snapshot import evaluate

URL = "https://www.tiktok.com/@dy3ko4nveu0o/video/7706032610681703702"
ROW = {"url": URL, "published_at": "2026-11-09T05:02:21+01:00",
       "duration": 6, "views": 72, "likes": 0, "comments": 0,
       "shares": 0, "reach": None, "completion_rate": None,
       "average_watch_seconds": None}

class SnapshotTests(unittest.TestCase):
    def test_not_due_then_once_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = str(Path(tmp) / "snapshot.json")
            def run(now):
                return evaluate({"now": now, "rows": [ROW], "state_path": state})
            self.assertEqual(run("2026-11-10T04:59:00+01:00"), [])
            first = run("2026-11-10T05:03:00+01:00")
            self.assertEqual(len(first), 1)
            self.assertEqual(first[0]["decision"], "DATEN UNZUREICHEND")
            self.assertEqual(run("2026-11-11T18:10:00+01:00"), [])
            saved = json.loads(Path(state).read_text())
            self.assertEqual(len(saved["completed"]), 1)

    def test_reject_untrusted_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [dict(ROW, url="https://evil.example/video/7706032610681703702"),
                    dict(ROW, url="https://www.tiktok.com.evil.example/video/7706032610681703702")]
            result = evaluate({"now":"2026-11-13T18:10:00+01:00",
                               "rows":rows,"state_path":str(Path(tmp)/"state.json")})
            self.assertEqual(result, [])

    def test_no_historical_24h_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = evaluate({"now":"2026-11-13T18:10:00+01:00",
                               "rows":[ROW],"state_path":str(Path(tmp)/"state.json")})
            self.assertIn("not guaranteed exact 24h", result[0]["note"])

if __name__ == "__main__":
    unittest.main()
