import os
import tempfile
import unittest
from src.video_job_queue import VideoQueue

class DurableQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "queue.sqlite")
        self.q = VideoQueue(self.path)
        self.job = self.q.create({"topic": "Swiss comedy"}, "job-1")

    def tearDown(self):
        self.q.close()
        self.tmp.cleanup()

    def test_reopen_and_cas(self):
        self.assertTrue(self.q.transition(self.job, "IDEA", "SCRIPT_READY"))
        self.assertFalse(self.q.transition(self.job, "IDEA", "SCRIPT_READY"))
        self.q.close()
        self.q = VideoQueue(self.path)
        self.assertEqual(self.q.get(self.job)["state"], "SCRIPT_READY")

    def test_no_skip_and_rights_gate(self):
        with self.assertRaises(ValueError):
            self.q.transition(self.job, "IDEA", "USER_APPROVED")
        with self.assertRaises(ValueError):
            self.q.transition(self.job, "CREATIVE_QA_PASSED", "RIGHTS_VERIFIED")
        self.assertEqual(self.q.get(self.job)["state"], "IDEA")

    def test_duplicate_id(self):
        with self.assertRaises(Exception):
            self.q.create({}, "job-1")

    def test_retry_limit(self):
        self.assertTrue(self.q.transition(self.job, "IDEA", "FAILED_RETRYABLE", max_retries=0))
        self.assertEqual(self.q.get(self.job)["state"], "BLOCKED")

    def test_upload_unknown_blocks(self):
        for old, new, evidence in [
            ("IDEA","SCRIPT_READY",{}),
            ("SCRIPT_READY","GENERATOR_SELECTED",{}),
            ("GENERATOR_SELECTED","RENDERING",{}),
            ("RENDERING","RENDERED",{}),
            ("RENDERED","TECHNICAL_QA_PASSED",{"ffprobe_passed":True}),
            ("TECHNICAL_QA_PASSED","CREATIVE_QA_PASSED",{"creative_score":90,"human_reviewed":True}),
            ("CREATIVE_QA_PASSED","RIGHTS_VERIFIED",{"commercial_rights_evidence":"licensed source"}),
            ("RIGHTS_VERIFIED","AWAITING_USER_APPROVAL",{}),
            ("AWAITING_USER_APPROVAL","USER_APPROVED",{"explicit_user_approval":"approval id"}),
        ]:
            self.assertTrue(self.q.transition(self.job, old, new, evidence))
        self.assertTrue(self.q.transition(self.job,"USER_APPROVED","UPLOAD_STARTED",upload_key="unique-upload-1"))
        self.assertTrue(self.q.transition(self.job,"UPLOAD_STARTED","FAILED_RETRYABLE"))
        self.assertEqual(self.q.get(self.job)["state"],"BLOCKED")

if __name__ == "__main__":
    unittest.main()
