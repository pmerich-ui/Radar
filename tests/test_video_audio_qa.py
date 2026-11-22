import unittest
from unittest.mock import patch
from src.video_qa_agent import inspect

PROBE='{"format":{"duration":"18.0"},"streams":[{"codec_type":"video","codec_name":"h264","pix_fmt":"yuv420p","width":1080,"height":1920,"r_frame_rate":"30/1"},{"codec_type":"audio","codec_name":"aac"}]}'
class Result:
    def __init__(self, code=0, stderr=""):
        self.returncode=code
        self.stderr=stderr

class VideoQATests(unittest.TestCase):
    @patch("src.video_qa_agent.Path.is_file",return_value=True)
    @patch("src.video_qa_agent.subprocess.check_output",return_value=PROBE)
    @patch("src.video_qa_agent.subprocess.run")
    def test_silent_audio_blocked(self, run, *_):
        run.side_effect=[Result(),Result(stderr="mean_volume: -inf dB")]
        self.assertEqual(inspect("draft.mp4")["reason"],"AUDIO_SILENT_OR_TOO_QUIET")
    @patch("src.video_qa_agent.Path.is_file",return_value=True)
    @patch("src.video_qa_agent.subprocess.check_output",return_value=PROBE)
    @patch("src.video_qa_agent.subprocess.run")
    def test_decode_error_blocked(self, run, *_):
        run.return_value=Result(code=1)
        self.assertEqual(inspect("draft.mp4")["reason"],"DECODE_FAILED")
    @patch("src.video_qa_agent.Path.is_file",return_value=True)
    @patch("src.video_qa_agent.subprocess.check_output",return_value=PROBE)
    @patch("src.video_qa_agent.subprocess.run")
    def test_non_silent_audio_not_publishable_without_creative_review(self, run, *_):
        run.side_effect=[Result(),Result(stderr="mean_volume: -24.0 dB")]
        result=inspect("draft.mp4")
        self.assertEqual(result["status"],"TECHNICAL_PASS")
        self.assertFalse(result["publishable"])
