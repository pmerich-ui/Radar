"""Regression tests for the durable production evidence chain."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from src.production_ledger import connect, create, transition, status

class ProductionLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = connect(Path(self.temp.name) / "jobs.sqlite")
        self.addCleanup(self.db.close)
        create(self.db, "job-1", {"concept": "Swiss mockumentary"})

    def advance(self, target, evidence=None):
        return transition(self.db, "job-1", target, evidence)

    def test_no_skipped_gates_or_double_processing(self):
        with self.assertRaises(ValueError):
            self.advance("UPLOADED", {"metricool_id": "1"})
        self.assertFalse(self.advance("IDEA"))
        self.assertEqual(status(self.db, "job-1")["version"], 0)

    def test_real_file_hash_and_approval_are_mandatory(self):
        for state in ("SCRIPT_READY", "GENERATOR_SELECTED", "RENDERING"):
            self.advance(state)
        mp4 = Path(self.temp.name) / "video.mp4"
        mp4.write_bytes(b"mock bytes: tests ledger only, not video QA")
        digest = hashlib.sha256(mp4.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            self.advance("RENDERED", {"mp4_path": str(mp4), "sha256": "wrong"})
        self.advance("RENDERED", {"mp4_path": str(mp4), "sha256": digest})
        with self.assertRaises(ValueError):
            self.advance("TECHNICAL_QA_PASSED")
        self.advance("TECHNICAL_QA_PASSED", {"technical_pass": True})
        with self.assertRaises(ValueError):
            self.advance("CREATIVE_QA_PASSED", {"score": 84, "reviewer": "qa"})
        self.advance("CREATIVE_QA_PASSED", {"score": 85, "reviewer": "qa"})
        with self.assertRaises(ValueError):
            self.advance("RIGHTS_VERIFIED", {"commercial_rights": True})
        self.advance("RIGHTS_VERIFIED", {"commercial_rights": True, "license_reference": "license-evidence"})
        self.advance("AWAITING_USER_APPROVAL")
        with self.assertRaises(ValueError):
            self.advance("USER_APPROVED", {"approved_sha256": "wrong", "approval_reference": "yes"})
        self.advance("USER_APPROVED", {"approved_sha256": digest, "approval_reference": "owner-confirmed"})
        self.advance("UPLOAD_STARTED")
        with self.assertRaises(ValueError):
            self.advance("UPLOADED")
        self.advance("UPLOADED", {"metricool_id": "post-1"})
        with self.assertRaises(ValueError):
            self.advance("PUBLISHED_VERIFIED", {"tiktok_id": "1", "tiktok_url": "https://www.tiktok.com/@x/video/1"})
        self.advance("PUBLISHED_VERIFIED", {"tiktok_id": "1", "tiktok_url": "https://www.tiktok.com/@x/video/1", "platform_confirmed": True})
        self.assertEqual(status(self.db, "job-1")["state"], "PUBLISHED_VERIFIED")
        self.assertFalse(self.advance("PUBLISHED_VERIFIED"))
        self.assertEqual(status(self.db, "job-1")["version"], 12)

    def test_no_retry_after_upload_started(self):
        for state in ("SCRIPT_READY", "GENERATOR_SELECTED", "RENDERING"):
            self.advance(state)
        mp4 = Path(self.temp.name) / "video.mp4"
        mp4.write_bytes(b"ledger fixture only")
        digest = hashlib.sha256(mp4.read_bytes()).hexdigest()
        self.advance("RENDERED", {"mp4_path": str(mp4), "sha256": digest})
        self.advance("TECHNICAL_QA_PASSED", {"technical_pass": True})
        self.advance("CREATIVE_QA_PASSED", {"score": 85, "reviewer": "qa"})
        self.advance("RIGHTS_VERIFIED", {"commercial_rights": True, "license_reference": "test"})
        self.advance("AWAITING_USER_APPROVAL")
        self.advance("USER_APPROVED", {"approved_sha256": digest, "approval_reference": "test"})
        self.advance("UPLOAD_STARTED")
        with self.assertRaisesRegex(ValueError, "Upload outcome uncertain"):
            self.advance("FAILED_RETRYABLE")
        self.assertEqual(status(self.db, "job-1")["state"], "UPLOAD_STARTED")

    def test_retry_budget_is_bounded(self):
        self.advance("SCRIPT_READY")
        for _ in range(3):
            self.advance("FAILED_RETRYABLE", {"reason": "transient generator failure"})
            self.advance("GENERATOR_SELECTED")
        with self.assertRaisesRegex(ValueError, "Retry budget exhausted"):
            self.advance("FAILED_RETRYABLE")
        self.assertEqual(status(self.db, "job-1")["state"], "GENERATOR_SELECTED")

    def test_restart_and_retry(self):
        self.advance("SCRIPT_READY")
        self.db.close()
        self.db = connect(Path(self.temp.name) / "jobs.sqlite")
        self.assertEqual(status(self.db, "job-1")["state"], "SCRIPT_READY")
        self.advance("FAILED_RETRYABLE", {"reason": "generator unavailable"})
        self.advance("GENERATOR_SELECTED")
        with self.assertRaises(ValueError):
            self.advance("PUBLISHED_VERIFIED")

if __name__ == "__main__":
    unittest.main()
