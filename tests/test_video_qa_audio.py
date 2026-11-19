"""Regression tests for technical QA fail-closed rules."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.video_qa_agent import inspect

class VideoQATests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "sample.mp4"
        self.path.write_bytes(b"test")
    def tearDown(self):
        self.temp.cleanup()
    def probe(self, audio=True, duration=18):
        streams = [{"codec_type":"video","codec_name":"h264","pix_fmt":"yuv420p",
                    "width":1080,"height":1920,"r_frame_rate":"30/1"}]
        if audio:
            streams.append({"codec_type":"audio","codec_name":"aac"})
        return json.dumps({"streams":streams,"format":{"duration":str(duration)}})
    @patch("src.video_qa_agent.subprocess.run")
    @patch("src.video_qa_agent.subprocess.check_output")
    def test_no_audio_blocked(self, probe, run):
        probe.return_value = self.probe(audio=False)
        self.assertEqual(inspect(self.path)["reason"], "VIDEO_PROBE_OR_DECODE_FAILED")
        run.assert_not_called()
    @patch("src.video_qa_agent.subprocess.run")
    @patch("src.video_qa_agent.subprocess.check_output")
    def test_too_long_blocked(self, probe, run):
        probe.return_value = self.probe(duration=22)
        self.assertEqual(inspect(self.path)["reason"], "VIDEO_SPEC_MISMATCH")
        run.assert_not_called()
    @patch("src.video_qa_agent.subprocess.run")
    @patch("src.video_qa_agent.subprocess.check_output")
    def test_silent_audio_blocked(self, probe, run):
        probe.return_value = self.probe()
        run.side_effect = [None, type("Result", (), {"stderr":"mean_volume: -inf dB"})()]
        self.assertEqual(inspect(self.path)["reason"], "AUDIO_SILENT_OR_TOO_QUIET")
    @patch("src.video_qa_agent.subprocess.run")
    @patch("src.video_qa_agent.subprocess.check_output")
    def test_valid_audio_not_publishable(self, probe, run):
        probe.return_value = self.probe()
        run.side_effect = [None, type("Result", (), {"stderr":"mean_volume: -20.0 dB"})()]
        result = inspect(self.path)
        self.assertEqual(result["status"], "TECHNICAL_PASS")
        self.assertFalse(result["publishable"])
if __name__ == "__main__":
    unittest.main()
