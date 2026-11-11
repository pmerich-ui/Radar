import unittest
from video_router.catalog import load_catalog, audit
from video_router.hf_space_probe import require_hf_generation_approval

class FreePlatformsTests(unittest.TestCase):
    def test_all_five_present(self):
        names = {x["name"] for x in load_catalog()}
        self.assertTrue({"Wan2.Video", "AIVideoFree", "Fabbo", "Vidnoz", "Hugging Face ZeroGPU"}.issubset(names))
    def test_catalogue_count(self):
        self.assertEqual(len(load_catalog()), 55)
    def test_no_free_platform_automatically_enabled(self):
        entries = [x for x in load_catalog() if x["name"] in {"Wan2.Video", "AIVideoFree", "Fabbo", "Vidnoz", "Hugging Face ZeroGPU"}]
        self.assertTrue(all(not x["automatic_adapter"] and not x["generation_enabled"] for x in entries))
    def test_no_live_quotes_means_blocked(self):
        self.assertTrue(all(x["state"] == "BLOCKED" for x in audit(load_catalog())))
    def test_hf_requires_every_check(self):
        args = dict(commercial_license_verified=True,quota_verified=True,model_supports_9_16=True,free_account_confirmed=True,approved_space_owner_terms=True)
        self.assertTrue(require_hf_generation_approval(**args))
        for key in args:
            x = dict(args);x[key]=False
            self.assertFalse(require_hf_generation_approval(**x))
if __name__ == "__main__":
    unittest.main()
