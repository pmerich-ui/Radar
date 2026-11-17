"""Fail-closed V5 creative-format regression checks.

Legacy slide-based renders may pass codec/dimension validation, but are not
photorealistic human-action videos and must never count as V5-ready.
"""
import unittest
from pathlib import Path


class V5CreativeGateTests(unittest.TestCase):
    def test_legacy_renderer_is_not_accepted_as_v5(self):
        source = (Path(__file__).resolve().parents[1] / "src" / "producer.py").read_text(encoding="utf-8")
        self.assertIn("def slide(", source)
        self.assertIn("from .visuals import frame", source)
        self.assertIn("zoompan=", source)
        # This test documents the currently unapproved legacy rendering path.
        # Remove it only when a real video generator and perceptual QA replace
        # the slide/zoompan implementation and are covered by positive tests.

    def test_publication_disabled_for_unverified_visuals(self):
        from src.publication_gate import publication_decision
        decision = publication_decision(
            qa_passed=False,
            rights_verified=False,
            factual_claims_verified=False,
            platform_tested=False,
            explicit_approval=False,
        )
        self.assertFalse(decision["allowed"])


if __name__ == "__main__":
    unittest.main()
