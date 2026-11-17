"""Regression: failed atomic manifest replacement preserves the previous queue."""
import json
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import producer


class AtomicManifestTests(unittest.TestCase):
    def test_replace_failure_preserves_manifest_and_cleans_temp(self):
        item = ("de-CH", "comedy", "test", "Atomic write fixture")
        def fake_render(_item, path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"test fixture, not a video")
            return {"sha256": "fixture-atomic-hash", "width": 1080, "height": 1920}
        with tempfile.TemporaryDirectory() as temp:
            old_cwd = os.getcwd()
            try:
                os.chdir(temp)
                Path("data").mkdir()
                original = '{"produced": []}\n'
                Path("data/produced.json").write_text(original)
                with patch.object(producer, "CATALOG", [item]), patch.object(producer, "render", side_effect=fake_render), patch.dict(os.environ, {"BATCH_SIZE": "1"}), patch("os.replace", side_effect=OSError("simulated replacement failure")):
                    with self.assertRaisesRegex(OSError, "simulated replacement failure"):
                        runpy.run_module("src.batch", run_name="__main__")
                self.assertEqual(Path("data/produced.json").read_text(), original)
                self.assertEqual(list(Path("data").glob(".produced-*.tmp")), [])
                self.assertEqual(json.loads(Path("data/produced.json").read_text())["produced"], [])
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
