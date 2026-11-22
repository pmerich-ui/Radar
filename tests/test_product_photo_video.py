import json
import tempfile
import unittest
from pathlib import Path
from src.product_photo_video import prepare

class ProductPhotoVideoTests(unittest.TestCase):
    def test_no_unlicensed_or_missing_assets(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"manifest.json"
            p.write_text(json.dumps({"assets":[{"path":"missing.jpg","license":"CC0-1.0",
                "source":"https://example.org","evidence":"https://example.org"}]*3}))
            with self.assertRaises(ValueError):
                prepare(p,Path(d)/"out.mp4")
    def test_empty_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"manifest.json"
            p.write_text('{"assets":[]}')
            with self.assertRaises(ValueError):
                prepare(p,Path(d)/"out.mp4")
if __name__=="__main__":
    unittest.main()
