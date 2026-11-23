"""Queue invariants: persistence, idempotency, approval, unsafe retry."""
import tempfile
import unittest
from pathlib import Path
from src.video_job_queue import Queue

class QueueTests(unittest.TestCase):
    def test_persistence_and_idempotency(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"queue.sqlite"
            q=Queue(path); job=q.create({"a":1},"fixed")
            self.assertEqual(q.create({"a":2},"fixed"),job)
            self.assertTrue(q.transition(job,"IDEA","SCRIPT_READY"))
            self.assertFalse(q.transition(job,"IDEA","SCRIPT_READY"))
            q.db.close()
            q=Queue(path)
            self.assertEqual(q.get(job)["state"],"SCRIPT_READY")
    def test_fail_closed_approval(self):
        with tempfile.TemporaryDirectory() as d:
            q=Queue(Path(d)/"queue.sqlite"); job=q.create({})
            states=("IDEA","SCRIPT_READY","GENERATOR_SELECTED","RENDERING","RENDERED","TECHNICAL_QA_PASSED","CREATIVE_QA_PASSED","RIGHTS_VERIFIED","AWAITING_USER_APPROVAL")
            for a,b in zip(states,states[1:]): self.assertTrue(q.transition(job,a,b))
            with self.assertRaises(ValueError): q.transition(job,"AWAITING_USER_APPROVAL","USER_APPROVED")
            self.assertTrue(q.transition(job,"AWAITING_USER_APPROVAL","USER_APPROVED",approval_id="approval-for-this-video"))
            self.assertTrue(q.transition(job,"USER_APPROVED","UPLOAD_STARTED"))
            self.assertTrue(q.transition(job,"UPLOAD_STARTED","UPLOADED"))
            with self.assertRaises(ValueError): q.transition(job,"UPLOADED","PUBLISHED_VERIFIED")
            self.assertTrue(q.transition(job,"UPLOADED","PUBLISHED_VERIFIED",platform_post_id="verified-platform-id"))
            with self.assertRaises(ValueError): q.transition(job,"PUBLISHED_VERIFIED","FAILED_RETRYABLE")
    def test_resume_without_double_render(self):
        with tempfile.TemporaryDirectory() as d:
            q=Queue(Path(d)/"queue.sqlite"); job=q.create({})
            q.transition(job,"IDEA","SCRIPT_READY")
            q.transition(job,"SCRIPT_READY","GENERATOR_SELECTED")
            q.transition(job,"GENERATOR_SELECTED","RENDERING")
            q.transition(job,"RENDERING","FAILED_RETRYABLE")
            self.assertFalse(q.resume(job))
            self.assertEqual(q.get(job)["state"],"FAILED_RETRYABLE")

if __name__=="__main__": unittest.main()
