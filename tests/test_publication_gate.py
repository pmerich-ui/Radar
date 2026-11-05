import os
import unittest
from unittest.mock import patch
from src.publication_gate import publication_decision

class PublicationGateTests(unittest.TestCase):
    def test_defaults_fail_closed(self):
        self.assertFalse(publication_decision().get("allowed"))
    def test_growth_needs_all_gates(self):
        with patch.dict(os.environ, {"MODE":"GROWTH","DRY_RUN":"false","PUBLISHING_ENABLED":"true"}):
            self.assertFalse(publication_decision(qa_passed=True).get("allowed"))
            self.assertTrue(publication_decision(qa_passed=True, rights_verified=True, factual_claims_verified=True, platform_tested=True, explicit_approval=True)["allowed"])
    def test_monetized_requires_extra_checks(self):
        with patch.dict(os.environ, {"MODE":"MONETIZED","DRY_RUN":"false","PUBLISHING_ENABLED":"true"}):
            self.assertFalse(publication_decision(qa_passed=True, rights_verified=True, factual_claims_verified=True, platform_tested=True, explicit_approval=True)["allowed"])
    def test_unknown_mode_fails(self):
        with patch.dict(os.environ, {"MODE":"UNKNOWN","DRY_RUN":"false","PUBLISHING_ENABLED":"true"}):
            self.assertEqual(publication_decision()["reason"],"INVALID_MODE")
