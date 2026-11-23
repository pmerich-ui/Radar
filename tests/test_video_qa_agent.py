"""Regression tests for FFmpeg audio-volume parsing and technical QA fail-closed behavior."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.video_qa_agent import inspect

class VideoQATests(unittest.TestCase):
    def _run(self, volume_text):
        probe = {"format":{"duration":"17.0"},"streams":[
            {"codec_type":"video","codec_name":"h264","pix_fmt":"yuv420p","width":1080,"height":1920,"r_frame_rate":"30/1"},
            {"codec_type":"audio","codec_name":"aac"}]}
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory)/"sample.mp4"
            video.write_bytes(b"test fixture; subprocess mocked")
            with patch("src.video_qa_agent.subprocess.check_output",return_value=json.dumps(probe)), patch(
                "src.video_qa_agent.subprocess.run",
                side_effect=[subprocess.CompletedProcess([],0,"",""),subprocess.CompletedProcess([],0,"",volume_text)]
            ):
                return inspect(video)

    def test_audible_audio_passes(self):
        result=self._run("[Parsed_volumedetect_0 @ 0x1] mean_volume: -18.4 dB\n")
        self.assertEqual(result["status"],"TECHNICAL_PASS")
        self.assertFalse(result["publishable"])

    def test_quiet_audio_blocked(self):
        result=self._run("[Parsed_volumedetect_0 @ 0x1] mean_volume: -52.1 dB\n")
        self.assertEqual(result["reason"],"AUDIO_SILENT_OR_TOO_QUIET")

    def test_missing_volume_blocked(self):
        result=self._run("no volume result")
        self.assertEqual(result["reason"],"AUDIO_SILENT_OR_TOO_QUIET")

if __name__=="__main__":
    unittest.main()
