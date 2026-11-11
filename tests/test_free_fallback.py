import os
import unittest
from unittest.mock import patch
from video_router.free_fallback import Provider, Status, eligible, route

class RouterTests(unittest.TestCase):
    def test_unknown_rights_block(self):
        self.assertFalse(eligible(Provider("a", 100, 1, False, True))[0])
    def test_insufficient_credits_block(self):
        self.assertFalse(eligible(Provider("a", 1, 2, True, True))[0])
    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            out = route([], lambda _: "https://example.com/video.mp4", lambda _: True)
            self.assertEqual(out[0].status, Status.HOLD)
    def test_fallback(self):
        providers = [Provider("first", 10, 1, True, True), Provider("second", 10, 1, True, True)]
        def generate(p):
            if p.name == "first":
                raise RuntimeError("temporary outage")
            return "https://example.com/real.mp4"
        with patch.dict(os.environ, {"DEALRADAR_ALLOW_FREE_GENERATION": "1"}):
            out = route(providers, generate, lambda url: url.endswith(".mp4"))
        self.assertEqual([x.status for x in out], [Status.FAILED, Status.GENERATED])
    def test_reject_unverified_output(self):
        with patch.dict(os.environ, {"DEALRADAR_ALLOW_FREE_GENERATION": "1"}):
            out = route([Provider("first", 10, 1, True, True)], lambda _: "https://example.com/a.mp4", lambda _: False)
        self.assertEqual(out[-1].status, Status.HOLD)

if __name__ == "__main__":
    unittest.main()
