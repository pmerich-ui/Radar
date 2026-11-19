"""Regression tests for the fail-closed technical MP4 gate (mocked FFmpeg)."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.readiness_audit import inspect_video


class TechnicalVideoGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "clip.mp4"
        self.path.write_bytes(b"x" * 12000)

    def inspect(self, *, duration=18, width=1080, height=1920,
                audio=True, volume="-21.0", decode_rc=0):
        streams = [{"codec_type": "video", "codec_name": "h264",
                    "width": width, "height": height, "r_frame_rate": "30/1"}]
        if audio:
            streams.append({"codec_type": "audio", "codec_name": "aac"})
        probe = json.dumps({"format": {"duration": str(duration)}, "streams": streams})
        def fake_run(args, **kwargs):
            if "volumedetect" in args:
                return subprocess.CompletedProcess(args, 0, "", f"mean_volume: {volume} dB")
            return subprocess.CompletedProcess(args, decode_rc, "", "")
        with patch("src.readiness_audit.subprocess.check_output", return_value=probe), \
             patch("src.readiness_audit.subprocess.run", side_effect=fake_run):
            return inspect_video(self.path)

    def test_valid_technical_clip_does_not_authorize_publication(self):
        result = self.inspect()
        self.assertTrue(result["technical_premium_pass"])
        self.assertFalse(result["publishable"])
        self.assertEqual(result["rights"], "RIGHTS_UNVERIFIED")
        self.assertEqual(result["creative_qa"], "NOT_VERIFIED")

    def test_rejects_duration_over_twenty_seconds(self):
        self.assertFalse(self.inspect(duration=21)["technical_premium_pass"])

    def test_rejects_wrong_resolution(self):
        self.assertFalse(self.inspect(width=720)["technical_premium_pass"])

    def test_rejects_missing_audio(self):
        self.assertFalse(self.inspect(audio=False)["technical_premium_pass"])

    def test_rejects_silence(self):
        self.assertFalse(self.inspect(volume="-inf")["technical_premium_pass"])

    def test_rejects_inaudibly_low_average_level(self):
        self.assertFalse(self.inspect(volume="-60.0")["technical_premium_pass"])

    def test_rejects_failed_full_decode(self):
        self.assertFalse(self.inspect(decode_rc=1)["technical_premium_pass"])


if __name__ == "__main__":
    unittest.main()
