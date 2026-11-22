import tempfile
import unittest
from pathlib import Path
from src.persistent_queue import Queue, STATES

class QueueTests(unittest.TestCase):
    def test_durable_deduplicated_and_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"queue.sqlite"
            q=Queue(path)
            job=q.add("campaign-1",{"product":"cable-clips"})
            assert q.add("campaign-1",{"product":"cable-clips"})["id"]==job["id"]
            jid=job["id"]
            assert q.advance(jid,"IDEA","SCRIPT_READY")
            assert not q.advance(jid,"IDEA","SCRIPT_READY")
            q.close()
            q=Queue(path)
            assert q.get(jid)["status"]=="SCRIPT_READY"
            q.close()
    def test_rights_and_approval_require_explicit_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            q=Queue(Path(d)/"queue.sqlite")
            jid=q.add("campaign-2",{"product":"strainer"})["id"]
            for a,b in zip(STATES[:8],STATES[1:9]):
                assert q.advance(jid,a,b,media_hash="hash1" if b=="RENDERED" else None,
                                 evidence_ref=f"verified-{b}" if b in ("TECHNICAL_QA_PASSED","CREATIVE_QA_PASSED","RIGHTS_VERIFIED") else None)
            assert q.get(jid)["status"]=="AWAITING_USER_APPROVAL"
            assert q.db.execute("SELECT COUNT(*) FROM job_evidence WHERE job_id=?",(jid,)).fetchone()[0]==3
            with self.assertRaises(ValueError):
                q.advance(jid,"AWAITING_USER_APPROVAL","USER_APPROVED")
            assert q.advance(jid,"AWAITING_USER_APPROVAL","USER_APPROVED",approval_ref="user-confirmation-video-123")
            assert q.advance(jid,"USER_APPROVED","UPLOAD_STARTED")
            with self.assertRaises(ValueError):
                q.advance(jid,"UPLOAD_STARTED","UPLOADED")
            assert q.advance(jid,"UPLOAD_STARTED","UPLOADED",external_post_id="post-123")
            with self.assertRaises(ValueError):
                q.advance(jid,"UPLOADED","PUBLISHED_VERIFIED")
            assert q.advance(jid,"UPLOADED","PUBLISHED_VERIFIED",evidence_ref="metricool-confirmed-post-123")
            assert not q.fail(jid,"PUBLISHED_VERIFIED","irrelevant")
            q.close()
    def test_same_key_different_payload_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            q=Queue(Path(d)/"queue.sqlite")
            first=q.add("campaign",{"product":"cable-clips"})
            with self.assertRaises(ValueError):
                q.add("campaign",{"product":"different-product"})
            assert q.get(first["id"])["status"]=="IDEA"
            q.close()
    def test_retry_limit(self):
        with tempfile.TemporaryDirectory() as d:
            q=Queue(Path(d)/"queue.sqlite")
            jid=q.add("campaign-3",{"product":"stand"})["id"]
            for i in range(3):
                assert q.fail(jid,"IDEA","temporary failure")
                if i<2: assert q.resume(jid)
            assert q.get(jid)["status"]=="BLOCKED"
            assert not q.resume(jid)
            q.close()
