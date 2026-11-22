"""Regression: upload cannot proceed without persisted QA and rights evidence."""
import tempfile
import unittest
from pathlib import Path
from src.persistent_queue import Queue


class UploadGateTests(unittest.TestCase):
    def test_approval_requires_persisted_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            q = Queue(Path(tmp) / "queue.sqlite")
            job = q.add("gate-test", {"campaign": "gate-test"})
            job_id = job["id"]
            states = [
                ("IDEA", "SCRIPT_READY"),
                ("SCRIPT_READY", "GENERATOR_SELECTED"),
                ("GENERATOR_SELECTED", "RENDERING"),
                ("RENDERING", "RENDERED"),
                ("RENDERED", "TECHNICAL_QA_PASSED"),
                ("TECHNICAL_QA_PASSED", "CREATIVE_QA_PASSED"),
                ("CREATIVE_QA_PASSED", "RIGHTS_VERIFIED"),
                ("RIGHTS_VERIFIED", "AWAITING_USER_APPROVAL"),
            ]
            for source, target in states:
                opts = {}
                if target == "RENDERED": opts["media_hash"] = "test-media-hash"
                if target.endswith("PASSED") or target == "RIGHTS_VERIFIED":
                    opts["evidence_ref"] = "test-evidence-" + target
                self.assertTrue(q.advance(job_id, source, target, **opts))
            q.db.execute("DELETE FROM job_evidence WHERE job_id=? AND state='RIGHTS_VERIFIED'", (job_id,))
            with self.assertRaisesRegex(ValueError, "Upload gate"):
                q.advance(job_id, "AWAITING_USER_APPROVAL", "USER_APPROVED", approval_ref="test-user-approval")
            self.assertEqual(q.get(job_id)["status"], "AWAITING_USER_APPROVAL")
            q.close()


if __name__ == "__main__":
    unittest.main()
