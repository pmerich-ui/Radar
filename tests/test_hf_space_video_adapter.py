"""Security and publication-gate tests for Hugging Face cloud adapter."""
import json
import unittest
from unittest.mock import patch
from src.hf_space_video_adapter import CloudRenderError, submit, validate_space_url, validate_api_name

class HuggingFaceSpaceAdapterTests(unittest.TestCase):
    def test_disabled_is_network_free(self):
        with patch("urllib.request.build_opener", side_effect=AssertionError("network called")):
            self.assertEqual(submit("https://example.hf.space", "predict", [], enabled=False)["status"], "DISABLED")

    def test_allow_valid_host_only(self):
        self.assertEqual(validate_space_url("https://demo-video.hf.space/"), "https://demo-video.hf.space")
        for url in ["https://example.com", "http://demo.hf.space",
                    "https://demo.hf.space.evil.com", "https://demo.hf.space:8443",
                    "https://user:password@demo.hf.space", "https://demo.hf.space/?x=1",
                    "https://demo.hf.space/other"]:
            with self.subTest(url=url), self.assertRaises(CloudRenderError):
                validate_space_url(url)

    def test_api_name_validation(self):
        self.assertEqual(validate_api_name("generate_video"), "generate_video")
        for name in ("../predict", "foo/bar", "", "a-b"):
            with self.subTest(name=name), self.assertRaises(CloudRenderError):
                validate_api_name(name)

    def test_inputs_must_be_small_list(self):
        with self.assertRaises(CloudRenderError):
            submit("https://demo.hf.space", "predict", {}, enabled=True)
        with self.assertRaises(CloudRenderError):
            submit("https://demo.hf.space", "predict", ["x" * 100_001], enabled=True)

    def test_success_does_not_claim_render_or_publication(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return b'{"event_id":"abc123"}'
        class Opener:
            def open(self, request, timeout):
                self.request = request
                return Response()
        opener = Opener()
        with patch("urllib.request.build_opener", return_value=opener):
            result = submit("https://demo.hf.space", "predict", ["safe"], enabled=True)
        self.assertEqual(opener.request.full_url, "https://demo.hf.space/gradio_api/call/predict")
        self.assertEqual(result["status"], "SUBMITTED_UNVERIFIED")
        self.assertIsNone(result["rendered_file"])
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(result["owner_approval"])

    def test_missing_event_id_is_failure(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return b'{}'
        class Opener:
            def open(self, request, timeout): return Response()
        with patch("urllib.request.build_opener", return_value=Opener()):
            with self.assertRaises(CloudRenderError):
                submit("https://demo.hf.space", "predict", [], enabled=True)

if __name__ == "__main__":
    unittest.main()
