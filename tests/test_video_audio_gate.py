"""Audio-gate regression tests use mocks, not real media."""
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

    def inspect_mock(self, audio, audible=True):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.mp4"
            path.write_bytes(b"fixture only")
            with patch("src.video_qa_agent.subprocess.check_output", return_value=self.probe(audio)), patch("src.video_qa_agent._audible_audio", return_value=audible) as check:
                result = inspect(path)
                if not audio:
                    check.assert_not_called()
                return result

    def test_missing_audio_blocks(self):
        result = self.inspect_mock(False)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["publishable"])

    def test_silent_audio_blocks(self):
        result = self.inspect_mock(True, False)
        self.assertEqual(result["reason"], "AUDIO_SILENT_OR_UNVERIFIED")
        self.assertFalse(result["publishable"])

    def test_audible_track_never_grants_publication(self):
        result = self.inspect_mock(True, True)
        self.assertEqual(result["status"], "TECHNICAL_PASS")
        self.assertFalse(result["publishable"])
        self.assertIn("listening_review", result["requires"])

if __name__ == "__main__":
    unittest.main()
