import unittest
from src.video_provider_router import registry, candidates, plan, fallback

class RouterTests(unittest.TestCase):
    def setUp(self):
        self.raw = '[{"name":"free","enabled":true,"commercial_rights":true,"supports_vertical":true,"credits":3,"cost_credits":0,"priority":1},{"name":"paid","enabled":true,"commercial_rights":true,"supports_vertical":true,"credits":10,"cost_credits":5,"priority":2}]'
    def test_free_only_by_default(self):
        self.assertEqual([p.name for p in candidates(registry(self.raw))], ["free"])
    def test_no_provider_fail_closed(self):
        self.assertEqual(plan("[]")["status"], "BLOCKED_NO_ELIGIBLE_PROVIDER")
    def test_fallback_on_confirmed_free_failure(self):
        r=fallback(registry(self.raw),lambda p: {"status":"FAILED","charged":False},5)
        self.assertEqual(len(r["attempts"]),2)
    def test_uncertain_attempt_stops(self):
        r=fallback(registry(self.raw),lambda p: {"status":"TIMEOUT"},5)
        self.assertEqual(len(r["attempts"]),1)
    def test_no_auto_publish(self):
        self.assertFalse(plan(self.raw)["publication_authorized"])
if __name__ == "__main__":
    unittest.main()
