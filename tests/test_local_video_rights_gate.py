"""Regression: the local illustration adapter must never be eligible for commercial routing."""
import unittest
from src.local_video_adapter import LOCAL
from src.video_provider_router import plan, registry


class LocalRightsGateTests(unittest.TestCase):
    def test_local_renderer_is_not_a_licensed_provider(self):
        provider = registry(LOCAL)[0]
        self.assertEqual(provider.name, "local_ffmpeg")
        self.assertFalse(provider.commercial_rights)
        self.assertEqual(provider.credits, 0)
        self.assertEqual(provider.cost_credits, 0)

    def test_local_renderer_cannot_enter_production(self):
        decision = plan(LOCAL)
        self.assertEqual(decision["status"], "BLOCKED_NO_ELIGIBLE_PROVIDER")
        self.assertEqual(decision["providers"], [])
        self.assertFalse(decision["publication_authorized"])


if __name__ == "__main__":
    unittest.main()
