"""Offline security and fail-closed tests for ComfyUI local adapter."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.comfyui_local_adapter import LocalRenderError, _local_url, submit_workflow

class ComfyUIAdapterTests(unittest.TestCase):
    def test_disabled_never_reads_or_calls_network(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network used")):
            self.assertEqual(submit_workflow("/nonexistent/workflow.json")["status"], "DISABLED")

    def test_reject_remote_and_unexpected_ports(self):
        for url in ("https://127.0.0.1:8188", "http://example.com:8188",
                    "http://127.0.0.1:8080", "http://127.0.0.1:8188?x=1",
                    "http://user:pass@localhost:8188"):
            with self.subTest(url=url):
                with self.assertRaises(LocalRenderError):
                    _local_url(url)

    def test_reject_invalid_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflow.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(LocalRenderError):
                submit_workflow(path, enabled=True)

    def test_submitted_is_not_rendered_or_publishable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflow.json"
            path.write_text(json.dumps({"1": {"class_type": "KSampler", "inputs": {}}}))
            class FakeResponse:
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, limit): return b'{"prompt_id":"test-prompt"}'
            with patch("urllib.request.urlopen", return_value=FakeResponse()) as request:
                result = submit_workflow(path, enabled=True)
            self.assertEqual(request.call_args.args[0].full_url, "http://127.0.0.1:8188/prompt")
            self.assertEqual(result["status"], "SUBMITTED_UNVERIFIED")
            self.assertFalse(result["publication_authorized"])
            self.assertFalse(result["owner_approval"])
            self.assertIsNone(result["rendered_file"])

if __name__ == "__main__":
    unittest.main()
