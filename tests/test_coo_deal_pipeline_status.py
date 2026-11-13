"""Offline regression tests: Awin pipeline failures must not look successful in CI."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import coo_deal_pipeline


class TestAwinExitStatus(unittest.TestCase):
    def invoke(self, status):
        with tempfile.TemporaryDirectory() as temp:
            pretend_file = str(Path(temp) / "src" / "coo_deal_pipeline.py")
            result = {
                "status": status,
                "reason": "TEST_ONLY",
                "candidates": 0,
                "briefs_created": 0,
                "publishable": False,
            }
            with patch.object(coo_deal_pipeline, "__file__", pretend_file), \
                 patch.object(coo_deal_pipeline, "run", return_value=result), \
                 patch("builtins.print"):
                exit_code = coo_deal_pipeline.main()
            written = json.loads((Path(temp) / "reports" / "coo_deal_pipeline.json").read_text(encoding="utf-8"))
            return exit_code, written

    def test_blocked_import_fails(self):
        code, report = self.invoke("BLOCKED")
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertFalse(report["publishable"])

    def test_valid_draft_review_exits_cleanly_without_publishing(self):
        code, report = self.invoke("DRAFT_REVIEW")
        self.assertEqual(code, 0)
        self.assertFalse(report["publishable"])

    def test_no_candidates_is_not_a_fabricated_failure(self):
        code, report = self.invoke("NO_CANDIDATES")
        self.assertEqual(code, 0)
        self.assertEqual(report["candidates"], 0)


if __name__ == "__main__":
    unittest.main()
