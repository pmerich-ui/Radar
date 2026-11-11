import unittest
from video_router.catalog import load_catalog, audit, provider_reasons
from video_router.provider_router import route_catalog

class CatalogTests(unittest.TestCase):
    def test_contains_all_original_plus_connected(self):
        rows = load_catalog()
        self.assertEqual(len(rows), 51)
        self.assertIn("Creative Claw", {r["name"] for r in rows})
        self.assertIn("fal.ai", {r["name"] for r in rows})
    def test_unknown_rights_never_ready(self):
        row = next(r for r in load_catalog() if r["name"] == "Kling AI")
        live = dict(authenticated_api=True, free_cost_chf=0, free_credits_remaining=500,
                    required_free_credits=1, license_checked_for_model=True,
                    aspect_ratio_9_16=True, min_resolution_480p=True,
                    free_account_allowed=True)
        self.assertTrue(provider_reasons(row, live))
    def test_prohibited_rights_never_ready(self):
        row = next(r for r in load_catalog() if r["name"] == "PixVerse")
        self.assertTrue(provider_reasons(row, dict(authenticated_api=True, free_cost_chf=0)))
    def test_all_blocked_without_authenticated_quotes(self):
        self.assertTrue(all(x["state"] == "BLOCKED" for x in audit(load_catalog())))
    def test_validated_runway_can_be_ready(self):
        row = next(r for r in load_catalog() if r["name"] == "Runway")
        live = dict(authenticated_api=True, free_cost_chf=0, free_credits_remaining=125,
                    required_free_credits=10, license_checked_for_model=True,
                    aspect_ratio_9_16=True, min_resolution_480p=True,
                    free_account_allowed=True)
        self.assertEqual(provider_reasons(row, live), [])
        live["free_cost_chf"] = 0.01
        self.assertTrue(provider_reasons(row, live))
    def test_open_source_needs_free_gpu(self):
        row = next(r for r in load_catalog() if r["name"] == "Wan 2.2")
        live = dict(authenticated_api=True, free_cost_chf=0, free_credits_remaining=1,
                    required_free_credits=0, license_checked_for_model=True,
                    aspect_ratio_9_16=True, min_resolution_480p=True,
                    free_account_allowed=True)
        self.assertIn("0 CHF GPU compute not verified", provider_reasons(row, live))
    def test_no_generation_without_optin(self):
        out = route_catalog({}, {}, lambda _: True)
        self.assertEqual(out["status"], "HOLD")
        self.assertEqual(out["attempts"], [])
    def test_no_adapter_never_generates(self):
        out = route_catalog({}, {}, lambda _: True, approved_free_generation=True)
        self.assertEqual(out["status"], "NO_VERIFIED_VIDEO")
        self.assertEqual(out["attempts"], [])
if __name__ == "__main__":
    unittest.main()
