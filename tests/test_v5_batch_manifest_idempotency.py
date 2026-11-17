"""Regression tests for V5 batch manifests; no video rendering or uploads."""
import json
import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import producer


class BatchManifestGateTests(unittest.TestCase):
    def test_legacy_output_never_becomes_publishable_and_is_idempotent(self):
        item = ("de-CH", "comedy", "test", "Test clip")
        def fake_render(_item, path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture only, not a real video")
            return {"sha256": "fixture-hash", "width": 1080, "height": 1920}

        with tempfile.TemporaryDirectory() as temp, patch.object(producer, "CATALOG", [item]), patch.object(producer, "render", side_effect=fake_render), patch.dict(os.environ, {"BATCH_SIZE": "1"}):
            old = os.getcwd()
            try:
                os.chdir(temp)
                runpy.run_module("src.batch", run_name="__main__")
                records = json.loads(Path("data/produced.json").read_text())["produced"]
                self.assertEqual(len(records), 1)
                record = records[0]
                self.assertEqual(record["status"], "LEGACY_RENDER_NOT_V5_APPROVED")
                self.assertIs(record["publishable"], False)
                self.assertIs(record["rights_verified"], False)
                self.assertIs(record["user_approved"], False)
                self.assertEqual(record["creative_qa"], "NOT_PASSED")
                report = json.loads(Path("output/report.json").read_text())
                self.assertEqual(report["publication"], "BLOCKED")
                self.assertEqual(report["v5_publishable"], 0)
                runpy.run_module("src.batch", run_name="__main__")
                records_again = json.loads(Path("data/produced.json").read_text())["produced"]
                self.assertEqual(len(records_again), 1)
                self.assertEqual(json.loads(Path("output/report.json").read_text())["new"], 0)
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
