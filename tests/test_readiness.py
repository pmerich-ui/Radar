import unittest
from src.readiness import audit

class ReadinessTests(unittest.TestCase):
    def test_empty_environment_is_not_ready(self):
        result=audit({})
        self.assertFalse(result["can_send_daily_report"])
        self.assertFalse(result["can_measure_clicks"])
        self.assertFalse(result["can_measure_confirmed_revenue"])
    def test_secrets_are_not_exposed(self):
        result=audit({"TELEGRAM_BOT_TOKEN":"private-value","TELEGRAM_CHAT_ID":"123"})
        self.assertTrue(result["can_send_daily_report"])
        self.assertNotIn("private-value",str(result))
    def test_rejects_insecure_url(self):
        result=audit({"CLICK_REPORT_URL":"http://example.com/report","CLICK_REPORT_TOKEN":"private"})
        self.assertFalse(result["can_measure_clicks"])

if __name__=="__main__":unittest.main()
