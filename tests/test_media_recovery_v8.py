import hashlib, tempfile, unittest
from pathlib import Path
from src.media_recovery_v8 import recover, publication_ready, inspect

class RecoveryTests(unittest.TestCase):
    def test_retry_then_alternative(self):
        seen=[]
        def fake(url,path):
            seen.append(url)
            if url=="first": raise OSError("DNS")
            path.write_bytes(b"video")
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.mp4"
            result=recover({"sources":[{"url":"first"},{"url":"second"}]},p,fake,lambda _:None)
            self.assertEqual(seen,["first"]*3+["second"])
            self.assertEqual(result["status"],"RENDERED")
            self.assertEqual(p.read_bytes(),b"video")
    def test_bad_hash_never_promoted(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.mp4"
            r=recover({"sha256":"wrong","sources":[{"url":"x"}]},p,lambda _,f:f.write_bytes(b"bad"),lambda _:None)
            self.assertEqual(r["status"],"FAILED_RETRYABLE")
            self.assertFalse(p.exists())
    def test_missing_rights_blocks(self):
        self.assertFalse(publication_ready({},{"status":"TECHNICAL_QA_PASSED","sha256":"x"},{}))
    def test_safety_gate(self):
        qa={"status":"TECHNICAL_QA_PASSED","sha256":"x"}
        e={"sha256":"x","rights_verified":True,"rights_source":"license","facts_verified":True,"disclosure_verified":True,"creative_score":86,"reviewer":"test","brand_id":7820933,"handle":"dy3ko4nveu0o"}
        self.assertTrue(publication_ready({},qa,e))
        self.assertFalse(publication_ready({"affiliate":True},qa,e))
        self.assertFalse(publication_ready({},qa,dict(e,sha256="other")))
        self.assertFalse(publication_ready({},qa,dict(e,creative_score=84)))
        self.assertFalse(publication_ready({},qa,dict(e,handle="other")))
    def test_invalid_mp4(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.mp4";p.write_bytes(b"not a video")
            self.assertEqual(inspect(p)["status"],"BLOCKED")
