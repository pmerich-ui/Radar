import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.video_qa_agent import inspect


def probe(with_audio=True, duration=18):
    streams = [{"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p",
                "width": 1080, "height": 1920, "r_frame_rate": "30/1"}]
    if with_audio:
        streams.append({"codec_type": "audio", "codec_name": "aac"})
    return json.dumps({"streams": streams, "format": {"duration": str(duration)}})


class TechnicalGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.mp4"
        self.path.write_bytes(b"fixture")

    def tearDown(self):
        self.tmp.cleanup()

    @patch("src.video_qa_agent.subprocess.check_output")
    def test_no_audio_fails_closed(self, check):
        check.return_value = probe(with_audio=False)
        self.assertEqual(inspect(self.path)["status"], "BLOCKED")

    @patch("src.video_qa_agent.subprocess.check_output")
    def test_duration_over_twenty_fails(self, check):
        check.return_value = probe(duration=21)
        self.assertEqual(inspect(self.path)["reason"], "VIDEO_SPEC_MISMATCH")

    @patch("src.video_qa_agent.subprocess.run")
    @patch("src.video_qa_agent.subprocess.check_output")
    def test_silent_audio_fails(self, check, run):
        check.return_value = probe()
        run.return_value.stderr = "[Parsed_volumedetect_0] max_volume: -inf dB"
        self.assertEqual(inspect(self.path)["reason"], "AUDIO_SILENT_OR_UNVERIFIED")

    @patch("src.video_qa_agent.subprocess.run")
    @patch("src.video_qa_agent.subprocess.check_output")
    def test_valid_probe_still_requires_human_approval(self, check, run):
        check.return_value = probe()
        run.return_value.stderr = "[Parsed_volumedetect_0] max_volume: -12.0 dB"
        result = inspect(self.path)
        self.assertEqual(result["status"], "TECHNICAL_PASS")
        self.assertFalse(result["publishable"])
        self.assertIn("audible_speech_review", result["requires"])


if __name__ == "__main__":
    unittest.main()
