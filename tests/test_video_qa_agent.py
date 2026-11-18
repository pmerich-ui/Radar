"""Regression tests for fail-closed video technical QA; no media publishing."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.video_qa_agent import inspect

def probe(duration=18, audio=True, width=1080):
    streams = [{"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p",
                "width": width, "height": 1920, "r_frame_rate": "30/1"}]
    if audio:
        streams.append({"codec_type": "audio", "codec_name": "aac"})
    return json.dumps({"format": {"duration": str(duration)}, "streams": streams})

class TechnicalQATests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "test.mp4"
        self.file.write_bytes(b"mocked-mp4")

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, info, volume="-12.3", decode_error=None):
        from subprocess import CompletedProcess, CalledProcessError
        def run(args, **kwargs):
            if "-xerror" in args and decode_error:
                raise CalledProcessError(1, args)
            return CompletedProcess(args, 0, "", f"max_volume: {volume} dB")
        with patch("src.video_qa_agent.subprocess.check_output", return_value=info), \
             patch("src.video_qa_agent.subprocess.run", side_effect=run) as mock_run:
            result = inspect(self.file)
        return result, mock_run.call_count

    def test_valid_video_never_publishable(self):
        result, calls = self.check(probe())
        self.assertEqual(result["status"], "TECHNICAL_PASS")
        self.assertFalse(result["publishable"])
        self.assertEqual(calls, 2)

    def test_missing_audio_blocks(self):
        result, calls = self.check(probe(audio=False))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(calls, 0)

    def test_duration_over_20_blocks(self):
        result, calls = self.check(probe(duration=21))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(calls, 0)

    def test_wrong_resolution_blocks(self):
        result, calls = self.check(probe(width=720))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(calls, 0)

    def test_silent_audio_blocks(self):
        result, _ = self.check(probe(), volume="-inf")
        self.assertEqual(result["reason"], "AUDIO_SILENT_OR_UNVERIFIED")

    def test_unverified_audio_blocks(self):
        result, _ = self.check(probe(), volume="-60.0")
        self.assertEqual(result["reason"], "AUDIO_SILENT_OR_UNVERIFIED")

    def test_decode_error_blocks(self):
        result, _ = self.check(probe(), decode_error=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "VIDEO_PROBE_FAILED")

if __name__ == "__main__":
    unittest.main()
