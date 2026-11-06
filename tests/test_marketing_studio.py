"""Offline checks for advertising director and technical video QA."""
import unittest
from src.advertising_director import build_brief
from src.video_qa_agent import inspect

class TestMarketingStudio(unittest.TestCase):
    def test_missing_evidence_blocks(self):
        self.assertEqual(build_brief({"product_name": "Test"})["status"], "BLOCKED")
    def test_approved_format_is_still_draft(self):
        result = build_brief({"product_name": "Kaffeemaschine", "merchant_name": "Shop",
                              "price_chf": 89.9, "product_url": "https://example.com"})
        self.assertEqual(result["status"], "DRAFT_REVIEW")
        self.assertFalse(result["publishable"])
        self.assertIn("owner_approval", result["blocked_until_verified"])
    def test_video_missing_is_blocked(self):
        self.assertEqual(inspect("/missing.mp4")["status"], "BLOCKED")

if __name__ == "__main__":
    unittest.main()
