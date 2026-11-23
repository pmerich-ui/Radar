"""Regression: parse real ffmpeg volumedetect output, not literal backslashes."""
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from src.video_qa_agent import inspect

class AudioVolumeTests(unittest.TestCase):
    def test_audible_ffmpeg_volume_is_accepted(self):
        probe='{"format":{"duration":"18.0"},"streams":[{"codec_type":"video","codec_name":"h264","pix_fmt":"yuv420p","width":1080,"height":1920,"r_frame_rate":"30/1"},{"codec_type":"audio","codec_name":"aac"}]}'
        with TemporaryDirectory() as d:
            path=Path(d)/"clip.mp4"
            path.write_bytes(b"test")
            with patch("src.video_qa_agent.subprocess.check_output",return_value=probe), patch("src.video_qa_agent.subprocess.run",side_effect=[SimpleNamespace(returncode=0),SimpleNamespace(returncode=0,stderr="[Parsed_volumedetect_0] mean_volume: -22.5 dB")]):
                self.assertEqual(inspect(path)["status"],"TECHNICAL_PASS")

if __name__=="__main__":
    unittest.main()
