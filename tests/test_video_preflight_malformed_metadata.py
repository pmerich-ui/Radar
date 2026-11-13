"""Regression: malformed ffprobe data must never bypass DealRadar QA."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "video_preflight.py"
spec = importlib.util.spec_from_file_location("dealradar_video_preflight", MODULE)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class MalformedMetadataTests(unittest.TestCase):
    def check_blocked(self, metadata):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "video.mp4"
            path.write_bytes(b"synthetic-nonempty-file")
            response = SimpleNamespace(returncode=0, stdout=json.dumps(metadata), stderr="")
            with patch.object(preflight, "run", return_value=response):
                result = preflight.inspect(path)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertFalse(result["publish_allowed"])
            self.assertFalse(result["rights_approved"])
            self.assertFalse(result["user_approved"])
            self.assertTrue(result["issues"])

    def test_null_dimensions(self):
        self.check_blocked({"streams": [{"codec_type": "video", "width": None, "height": 1920}],
                            "format": {"duration": "16"}})

    def test_invalid_stream_collection(self):
        self.check_blocked({"streams": None, "format": {"duration": "16"}})

    def test_nan_duration(self):
        self.check_blocked({"streams": [{"codec_type": "video", "width": 1080, "height": 1920}],
                            "format": {"duration": "NaN"}})

    def test_zero_height(self):
        self.check_blocked({"streams": [{"codec_type": "video", "width": 1080, "height": 0}],
                            "format": {"duration": "16"}})


if __name__ == "__main__":
    unittest.main()
