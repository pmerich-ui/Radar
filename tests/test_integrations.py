import unittest
from src.integrations import status, can_publish, revenue_state

class IntegrationTests(unittest.TestCase):
    def test_no_runtime_secrets_means_no_connection(self):
        self.assertTrue(all(not x["configured"] and not x["verified"] for x in status({})))
    def test_env_does_not_prove_verification(self):
        rows = status({"AWIN_API_TOKEN": "dummy", "AWIN_PUBLISHER_ID": "dummy"})
        self.assertTrue(rows[0]["configured"])
        self.assertFalse(rows[0]["verified"])
        self.assertFalse(rows[0]["production_allowed"])
    def test_publish_gate(self):
        self.assertFalse(can_publish(verified_deal=True, qa_passed=True, platform_approved=False, draft_confirmed=True))
        self.assertTrue(can_publish(verified_deal=True, qa_passed=True, platform_approved=True, draft_confirmed=True))
    def test_missing_revenue_not_zero(self):
        self.assertEqual(revenue_state(awin_connected=False,transactions_checked=False)["status"],"unmeasurable")
        self.assertEqual(revenue_state(awin_connected=True,transactions_checked=True,confirmed_chf=0)["confirmed_chf"],0.0)

if __name__ == "__main__":
    unittest.main()
