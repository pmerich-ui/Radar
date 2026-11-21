import tempfile
import unittest
from src.durable_video_queue import Queue, Conflict, ORDER

class DurableQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.q=Queue(self.tmp.name+"/queue.sqlite")
        self.id=self.q.add("fixed-id")
    def tearDown(self): self.tmp.cleanup()
    def test_idempotent_create_and_restart(self):
        self.assertEqual(self.q.add("fixed-id"),self.id)
        self.q.transition(self.id,"IDEA","SCRIPT_READY")
        self.assertEqual(Queue(self.tmp.name+"/queue.sqlite").get(self.id)["state"],"SCRIPT_READY")
    def test_duplicate_transition_blocked(self):
        self.q.transition(self.id,"IDEA","SCRIPT_READY")
        with self.assertRaises(Conflict): self.q.transition(self.id,"IDEA","SCRIPT_READY")
    def test_gate_fail_closed(self):
        for a,b in zip(ORDER,ORDER[1:]):
            if b=="TECHNICAL_QA_PASSED":
                with self.assertRaises(Conflict): self.q.transition(self.id,a,b)
            if b=="CREATIVE_QA_PASSED":
                with self.assertRaises(Conflict): self.q.transition(self.id,a,b)
            if b=="RIGHTS_VERIFIED":
                with self.assertRaises(Conflict): self.q.transition(self.id,a,b)
            if b=="USER_APPROVED":
                with self.assertRaises(Conflict): self.q.transition(self.id,a,b)
            evidence={"technical_ok":True} if b=="TECHNICAL_QA_PASSED" else (
                {"creative_ok":True} if b=="CREATIVE_QA_PASSED" else (
                {"rights_ok":True} if b=="RIGHTS_VERIFIED" else (
                {"approval_ok":True} if b=="USER_APPROVED" else {})))
            self.q.transition(self.id,a,b,evidence,publish_key="unique-pub" if b=="UPLOAD_STARTED" else None)
        self.assertEqual(self.q.get(self.id)["state"],"PUBLISHED_VERIFIED")
    def test_retry_limit(self):
        self.q.transition(self.id,"IDEA","FAILED_RETRYABLE")
        self.q.transition(self.id,"FAILED_RETRYABLE","IDEA")
        self.q.transition(self.id,"IDEA","FAILED_RETRYABLE",max_retries=1)
        self.q.transition(self.id,"FAILED_RETRYABLE","IDEA")
        with self.assertRaises(Conflict): self.q.transition(self.id,"IDEA","FAILED_RETRYABLE",max_retries=1)

    def test_publication_key_cannot_be_preassigned(self):
        with self.assertRaises(Conflict):
            self.q.transition(self.id,"IDEA","SCRIPT_READY",publish_key="premature")
        self.assertEqual(self.q.get(self.id)["state"],"IDEA")
        self.assertIsNone(self.q.get(self.id)["publish_key"])

    def test_evidence_cannot_be_preapproved(self):
        with self.assertRaises(Conflict):
            self.q.transition(self.id,"IDEA","SCRIPT_READY",{"approval_ok":True})
        self.assertEqual(self.q.get(self.id)["state"],"IDEA")

    def test_upload_outcome_cannot_be_automatically_retried(self):
        evidence_by_target = {
            "TECHNICAL_QA_PASSED":{"technical_ok":True},
            "CREATIVE_QA_PASSED":{"creative_ok":True},
            "RIGHTS_VERIFIED":{"rights_ok":True},
            "USER_APPROVED":{"approval_ok":True},
        }
        for a,b in zip(ORDER,ORDER[1:]):
            self.q.transition(self.id,a,b,evidence_by_target.get(b),publish_key="pub-1" if b=="UPLOAD_STARTED" else None)
            if b=="UPLOAD_STARTED":
                with self.assertRaises(Conflict):
                    self.q.transition(self.id,"UPLOAD_STARTED","FAILED_RETRYABLE")
            if b=="UPLOADED":
                with self.assertRaises(Conflict):
                    self.q.transition(self.id,"UPLOADED","FAILED_RETRYABLE")
        self.assertEqual(self.q.get(self.id)["state"],"PUBLISHED_VERIFIED")

if __name__=="__main__": unittest.main()
