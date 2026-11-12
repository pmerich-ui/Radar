#!/usr/bin/env python3
"""Fail-closed checks for the V5 creative backlog. No publishing."""
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "production" / "v6_comedy_idea_backlog.json"

class BacklogSafetyTest(unittest.TestCase):
    def test_creative_and_publication_invariants(self):
        data = json.loads(BACKLOG.read_text(encoding="utf-8"))
        self.assertEqual(data["project"], "DealRadar Schweiz")
        self.assertGreaterEqual(data["quality_threshold"], 85)
        self.assertIs(data["publication_allowed"], False)
        self.assertIs(data["rights_verified"], False)
        self.assertIs(data["ai_disclosure_required"], True)
        self.assertIs(data["commercial_claims_require_evidence"], True)
        self.assertEqual(data["generated_videos"], 0)
        ideas = data["ideas"]
        self.assertEqual(len(ideas), 10)
        self.assertEqual(len({i["id"] for i in ideas}), 10)
        self.assertEqual(Counter(i["category"] for i in ideas),
                         {"comedy": 6, "deal_comedy": 3, "verified_product_test": 1})
        for idea in ideas:
            with self.subTest(idea=idea["id"]):
                self.assertIn(idea["style"], {"photoreal", "dance"})
                self.assertEqual(idea["status"], "IDEA_ONLY")
                self.assertIsNone(idea["video_path"])
                self.assertEqual(idea["technical_qa"], "NOT_CHECKED")
                self.assertEqual(idea["rights_qa"], "NOT_CHECKED")
                self.assertIs(idea["user_approved"], False)
                self.assertIsNone(idea["published_url"])
                self.assertTrue(idea["concept"].strip())
        self.assertEqual(data["production_status"], "IDEAS_ONLY_NOT_RENDERED")

if __name__ == "__main__":
    unittest.main()
