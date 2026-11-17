"""Offline checks for advertising director and technical video QA."""
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, Mock
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
    def test_technical_gate_rejects_missing_audio_and_long_video(self):
        from src import video_qa_agent as qa
        def probe(seconds, with_audio=True):
            streams = [{"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p",
                        "width": 1080, "height": 1920, "r_frame_rate": "30/1"}]
            if with_audio:
                streams.append({"codec_type": "audio", "codec_name": "aac"})
            return json.dumps({"streams": streams, "format": {"duration": str(seconds)}})
        with TemporaryDirectory() as directory:
            path = Path(directory) / "test.mp4"
            path.write_bytes(b"not a real MP4; probe is mocked")
            with patch.object(qa.subprocess, "check_output", return_value=probe(18, False)):
                self.assertEqual(qa.inspect(path)["reason"], "VIDEO_SPEC_MISMATCH")
            with patch.object(qa.subprocess, "check_output", return_value=probe(25)):
                self.assertEqual(qa.inspect(path)["reason"], "VIDEO_SPEC_MISMATCH")

    def test_technical_gate_blocks_silent_audio_and_keeps_publish_blocked(self):
        from src import video_qa_agent as qa
        probe = json.dumps({"streams": [
            {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p",
             "width": 1080, "height": 1920, "r_frame_rate": "30/1"},
            {"codec_type": "audio", "codec_name": "aac"}],
            "format": {"duration": "18"}})
        with TemporaryDirectory() as directory:
            path = Path(directory) / "test.mp4"
            path.write_bytes(b"test")
            with patch.object(qa.subprocess, "check_output", return_value=probe):
                with patch.object(qa.subprocess, "run", side_effect=[
                    Mock(returncode=0), Mock(returncode=0, stderr="max_volume: -inf dB")]):
                    self.assertEqual(qa.inspect(path)["reason"], "AUDIO_SILENT_OR_TOO_QUIET")
                with patch.object(qa.subprocess, "run", side_effect=[
                    Mock(returncode=0), Mock(returncode=0, stderr="max_volume: -9.0 dB")]):
                    result = qa.inspect(path)
                    self.assertEqual(result["status"], "TECHNICAL_PASS")
                    self.assertFalse(result["publishable"])

    def test_video_missing_is_blocked(self):
        self.assertEqual(inspect("/missing.mp4")["status"], "BLOCKED")

if __name__ == "__main__":
    unittest.main()
