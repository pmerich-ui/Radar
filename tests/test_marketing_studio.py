"""Offline checks for advertising director and technical video QA."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
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
    def test_silent_mp4_is_blocked(self):
        probe = {"format": {"duration": "18.0"}, "streams": [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p",
             "width": 1080, "height": 1920, "r_frame_rate": "30/1"}]}
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "test.mp4"
            video.write_bytes(b"test")
            with patch("src.video_qa_agent.subprocess.check_output", return_value=json.dumps(probe)):
                result = inspect(video)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["publishable"])

    def test_audio_stream_still_requires_manual_approval(self):
        probe = {"format": {"duration": "18.0"}, "streams": [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p",
             "width": 1080, "height": 1920, "r_frame_rate": "30/1"},
            {"codec_type": "audio", "codec_name": "aac"}]}
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "test.mp4"
            video.write_bytes(b"test")
            with patch("src.video_qa_agent.subprocess.check_output", return_value=json.dumps(probe)):
                result = inspect(video)
        self.assertEqual(result["status"], "TECHNICAL_PASS")
        self.assertFalse(result["publishable"])

    def test_video_missing_is_blocked(self):
        self.assertEqual(inspect("/missing.mp4")["status"], "BLOCKED")

if __name__ == "__main__":
    unittest.main()
