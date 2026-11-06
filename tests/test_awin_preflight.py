"""Offline tests: Agent 05 preflight never exposes credentials."""
import unittest
from src.awin_preflight import check

class TestPreflight(unittest.TestCase):
    def test_missing_secret(self):
        result = check("")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "AWIN_FEED_URL_NOT_CONFIGURED")

    def test_invalid_secret(self):
        result = check("https://evil.example/secret")
        self.assertEqual(result["reason"], "AWIN_FEED_URL_INVALID")

    def test_valid_secret_never_echoed(self):
        secret = "https://productdata.awin.com/datafeed/download/key-PRIVATE"
        result = check(secret)
        self.assertEqual(result["status"], "READY")
        self.assertNotIn("PRIVATE", str(result))

if __name__ == "__main__":
    unittest.main()
