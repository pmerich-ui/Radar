#!/usr/bin/env python3
"""Regression tests for the fail-closed DealRadar publication gate. Offline only."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from publication_gate import decide

class PublicationGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p=Path(self.tmp.name)/"video.mp4"
        p.write_bytes(b"fixture-not-a-real-video")
        self.job={
            "job_id":"test-001","technical_pass":True,"visual_qa_score":90,
            "commercial_rights_verified":True,"advertising_claims_verified":True,
            "ai_disclosure_ready":True,"explicit_user_approval":True,
            "video_path":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
            "technical_report":{"status":"TECHNICAL_PASS"}
        }
        self.ledger={"published_jobs":{},"upload_attempts":{}}
    def test_manual_handoff_only(self):
        self.assertEqual(decide(self.job,self.ledger)["reason"],"eligible_for_manual_publish_handoff_only")
    def test_missing_approval_blocks(self):
        self.job["explicit_user_approval"]=False
        self.assertFalse(decide(self.job,self.ledger)["allowed"])
    def test_missing_rights_blocks(self):
        self.job["commercial_rights_verified"]=False
        self.assertFalse(decide(self.job,self.ledger)["allowed"])
    def test_qa_threshold_blocks(self):
        self.job["visual_qa_score"]=84
        self.assertFalse(decide(self.job,self.ledger)["allowed"])
    def test_hash_mismatch_blocks(self):
        self.job["sha256"]="0"*64
        self.assertFalse(decide(self.job,self.ledger)["allowed"])
    def test_existing_publication_blocks(self):
        self.ledger["published_jobs"]["test-001"]="https://www.tiktok.com/example"
        self.assertEqual(decide(self.job,self.ledger)["reason"],"already_published")
    def test_uncertain_upload_blocks(self):
        self.ledger["upload_attempts"]["test-001"]={"status":"unknown"}
        self.assertFalse(decide(self.job,self.ledger)["allowed"])
    def test_technical_report_blocks(self):
        self.job["technical_report"]["status"]="BLOCKED"
        self.assertFalse(decide(self.job,self.ledger)["allowed"])
    def test_missing_file_blocks(self):
        self.job["video_path"]=str(Path(self.tmp.name)/"missing.mp4")
        self.assertFalse(decide(self.job,self.ledger)["allowed"])

if __name__=="__main__":
    unittest.main()
