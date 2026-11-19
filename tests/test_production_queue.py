import os
import tempfile
import unittest
from src.production_queue import Queue

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=os.path.join(self.tmp.name,"jobs.db")
        self.q=Queue(self.path)
        self.id=self.q.add("job-1")
    def tearDown(self):
        self.q.db.close()
        self.tmp.cleanup()
    def test_idempotent_creation_and_restart(self):
        self.assertEqual(self.q.add("job-1"),self.id)
        other=Queue(self.path)
        self.assertEqual(other.get(self.id)["state"],"IDEA")
        other.db.close()
    def test_atomic_cas(self):
        self.assertTrue(self.q.transition(self.id,"IDEA","SCRIPT_READY"))
        self.assertFalse(self.q.transition(self.id,"IDEA","SCRIPT_READY"))
    def test_upload_blocked_without_gates(self):
        self.q.db.execute("UPDATE jobs SET state='USER_APPROVED' WHERE id=?",(self.id,))
        with self.assertRaises(ValueError):
            self.q.transition(self.id,"USER_APPROVED","UPLOAD_STARTED",upload_key="x")
    def test_lease_prevents_double_claim(self):
        self.assertTrue(self.q.claim(self.id))
        self.assertFalse(self.q.claim(self.id))
    def test_requires_evidence(self):
        self.q.db.execute("UPDATE jobs SET state='RENDERED' WHERE id=?",(self.id,))
        with self.assertRaises(ValueError):
            self.q.transition(self.id,"RENDERED","TECHNICAL_QA_PASSED")
    def test_no_duplicate_upload_keys(self):
        for id in ("a","b"):
            self.q.add(id)
            self.q.db.execute("""UPDATE jobs SET state='USER_APPROVED',technical_pass=1,
                creative_score=90,rights_verified=1,approval_id='specific' WHERE id=?""",(id,))
        self.assertTrue(self.q.transition("a","USER_APPROVED","UPLOAD_STARTED",upload_key="same"))
        with self.assertRaises(Exception):
            self.q.transition("b","USER_APPROVED","UPLOAD_STARTED",upload_key="same")

if __name__=="__main__":
    unittest.main()
