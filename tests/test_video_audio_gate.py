"""Regression checks for the technical audio gate; no publishing authorization."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.video_qa_agent import inspect

class VideoAudioGateTests(unittest.TestCase):
    def probe(self, audio):
        streams = [{"codec_type":"video","codec_name":"h264","pix_fmt":"yuv420p","width":1080,"height":1920,"r_frame_rate":"30/1"}]
        if audio:
            streams.append({"codec_type":"audio","codec_name":"aac"})
        return json.dumps({"streams":streams,"format":{"duration":"20.0"}})

    def test_missing_audio_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.mp4"
            path.write_bytes(b"test fixture, not a playable MP4")
            with patch("src.video_qa_agent.subprocess.check_output",return_value=self.probe(False)):
                result = inspect(path)
            self.assertEqual(result["status"],"BLOCKED")
            self.assertFalse(result["publishable"])

    def test_audio_track_never_grants_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.mp4"
            path.write_bytes(b"test fixture, not a playable MP4")
            with patch("src.video_qa_agent.subprocess.check_output",return_value=self.probe(True)):
                result = inspect(path)
            self.assertEqual(result["status"],"TECHNICAL_PASS")
            self.assertFalse(result["publishable"])
            self.assertIn("rights",result["requires"])

if __name__ == "__main__":
    unittest.main()
