import os
import unittest
from unittest.mock import patch
import daily_report

class DailyReportTests(unittest.TestCase):
    def test_no_secrets_does_not_invent_revenue(self):
        with patch.dict(os.environ, {}, clear=True):
            result = daily_report.report()
        self.assertIn("nicht messbar", result)
        self.assertIn("Awin-Provision CHF", result)
        self.assertIn("Awin-Provision EUR", result)

    def test_no_telegram_secrets_is_dry_run(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(daily_report.main(), 0)

    def test_bad_tracker_response_fails_closed(self):
        with patch.dict(os.environ, {"CLICK_REPORT_URL": "https://example.com/report", "CLICK_REPORT_TOKEN": "test"}, clear=True):
            with patch.object(daily_report, "get_json", return_value={"unexpected": []}):
                result = daily_report.report()
        self.assertIn("nicht messbar (Abruf fehlgeschlagen)", result)

if __name__ == "__main__":
    unittest.main()
