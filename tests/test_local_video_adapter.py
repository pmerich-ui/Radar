import unittest
from unittest.mock import patch
from src.local_video_adapter import run

class LocalVideoAdapterTests(unittest.TestCase):
    @patch("src.local_video_adapter.inspect", return_value={"status":"TECHNICAL_PASS"})
    @patch("src.local_video_adapter.render")
    def test_routes_and_blocks_publication(self, render, inspect):
        result = run("output/router-test.mp4")
        self.assertEqual(result["status"], "RENDERED_UNREVIEWED")
        self.assertFalse(result["publication_authorized"])
        self.assertIsNone(result["quality_score"])
        render.assert_called_once()
if __name__ == "__main__":
    unittest.main()
