"""Additional concurrency and publication-key regression tests (development only)."""
import tempfile
import unittest
from src.durable_video_queue import Queue, Conflict, ORDER

EVIDENCE = {
    "TECHNICAL_QA_PASSED": {"technical_ok": True},
    "CREATIVE_QA_PASSED": {"creative_ok": True},
    "RIGHTS_VERIFIED": {"rights_ok": True},
    "USER_APPROVED": {"approval_ok": True},
}

class PublicationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.q = Queue(self.tmp.name + "/queue.sqlite")
    def tearDown(self):
        self.tmp.cleanup()
    def advance_to_upload(self, job_id, key):
        self.q.add(job_id)
        for old, new in zip(ORDER, ORDER[1:]):
            self.q.transition(job_id, old, new, evidence=EVIDENCE.get(new),
                              publish_key=key if new == "UPLOAD_STARTED" else None)
            if new == "UPLOAD_STARTED":
                return

    def test_publication_key_unique_across_jobs(self):
        self.advance_to_upload("first", "shared-publication-key")
        self.q.add("second")
        for old, new in zip(ORDER, ORDER[1:]):
            if new == "UPLOAD_STARTED":
                with self.assertRaises(Exception):
                    self.q.transition("second", old, new, publish_key="shared-publication-key")
                self.assertEqual(self.q.get("second")["state"], "USER_APPROVED")
                break
            self.q.transition("second", old, new, evidence=EVIDENCE.get(new))

    def test_upload_state_survives_restart_and_rejects_retry(self):
        self.advance_to_upload("job", "unique-key")
        restarted = Queue(self.tmp.name + "/queue.sqlite")
        self.assertEqual(restarted.get("job")["state"], "UPLOAD_STARTED")
        with self.assertRaises(Conflict):
            restarted.transition("job", "UPLOAD_STARTED", "FAILED_RETRYABLE")
        with self.assertRaises(Conflict):
            restarted.transition("job", "UPLOAD_STARTED", "UPLOAD_STARTED")

    def test_no_publication_without_explicit_approval_evidence(self):
        self.q.add("unapproved")
        for old, new in zip(ORDER, ORDER[1:]):
            if new == "USER_APPROVED":
                with self.assertRaises(Conflict):
                    self.q.transition("unapproved", old, new)
                self.assertEqual(self.q.get("unapproved")["state"], "AWAITING_USER_APPROVAL")
                return
            self.q.transition("unapproved", old, new, evidence=EVIDENCE.get(new))
        self.fail("Approval gate not reached")

if __name__ == "__main__":
    unittest.main()
