"""Regression tests for fail-closed media QA. No publishing or paid generation."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.strict_media_qa import inspect


class StrictMediaQATests(unittest.TestCase):
    def test_missing_file_fails_closed(self):
        result = inspect("/nonexistent/dealradar-video.mp4")
        self.assertFalse(result["passed"])

    def test_invalid_media_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.mp4"
            path.write_bytes(b"not-a-video" * 2000)
            result = inspect(path)
            self.assertFalse(result["passed"])
            self.assertFalse(result["publication_allowed"])

    def test_valid_technical_checks_never_authorize_publication(self):
        probe = {"format": {"duration": "18.0"}, "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
            {"codec_type": "audio", "codec_name": "aac"}]}
        def fake_run(args, timeout=180):
            if args[0] == "ffprobe":
                return subprocess.CompletedProcess(args, 0, json.dumps(probe), "")
            if "volumedetect" in args:
                return subprocess.CompletedProcess(args, 0, "", "mean_volume: -18.0 dB")
            return subprocess.CompletedProcess(args, 0, "", "")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.mp4"
            path.write_bytes(b"x" * 12000)
            with patch("src.strict_media_qa._run", side_effect=fake_run):
                result = inspect(path)
        self.assertTrue(result["passed"])
        self.assertFalse(result["publication_allowed"])
        self.assertEqual(result["evidence"]["commercial_rights"], "RIGHTS_UNVERIFIED")
        self.assertEqual(result["evidence"]["creative_review"], "REQUIRED")

    def test_silent_audio_fails(self):
        probe = {"format": {"duration": "18"}, "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920},
            {"codec_type": "audio", "codec_name": "aac"}]}
        def fake_run(args, timeout=180):
            if args[0] == "ffprobe":
                return subprocess.CompletedProcess(args, 0, json.dumps(probe), "")
            if "volumedetect" in args:
                return subprocess.CompletedProcess(args, 0, "", "mean_volume: -inf dB")
            return subprocess.CompletedProcess(args, 0, "", "")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "silent.mp4"
            path.write_bytes(b"x" * 12000)
            with patch("src.strict_media_qa._run", side_effect=fake_run):
                result = inspect(path)
        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["audio_not_silent"])


if __name__ == "__main__":
    unittest.main()
