"""Offline regression tests: no accidental release and no fabricated TikTok success."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.metricool_mcp_bridge import ReleaseBlocked, ReleaseLedger, build_update, dispatch


SHA = "a"*64
QA = {"status": "TECHNICAL_QA_PASSED", "sha256": SHA}
EVIDENCE = {"sha256": SHA, "rights_verified": True, "rights_source": "official terms",
            "facts_verified": True, "disclosure_verified": True,
            "creative_score": 92, "reviewer": "verified-reviewer",
            "brand_id": 7820933, "handle": "dy3ko4nveu0o"}
POST = {"id": 443234750, "uuid": "stable-uuid", "providers": [{"network": "tiktok"}],
        "text": "Original Swiss shopping comedy #KI",
        "media": ["https://static.metricool.com/old.mp4"],
        "tiktokData": {"title": "DealRadar: Heidi", "isAigc": True}}
WHEN = datetime(2099, 11, 26, 21, 35, tzinfo=ZoneInfo("Europe/Zurich"))
MEDIA = "https://static.metricool.com/planner/202611/new.mp4"


class TestMetricoolMCPBridge(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = ReleaseLedger(Path(self.temp.name)/"queue.sqlite")

    def tearDown(self):
        self.ledger.db.close()
        self.temp.cleanup()

    def test_production_payload_enables_automatic_publish(self):
        import json
        args = build_update(POST, MEDIA, QA, EVIDENCE, {}, WHEN)
        body = json.loads(args["info"])
        self.assertIs(body["autoPublish"], True)
        self.assertIs(body["draft"], False)
        self.assertEqual(body["media"], [MEDIA])
        self.assertEqual(args["uuid"], POST["uuid"])
        self.assertEqual(POST["media"], ["https://static.metricool.com/old.mp4"])

    def test_cannot_publish_without_real_quality_evidence(self):
        with self.assertRaises(ReleaseBlocked):
            build_update(POST, MEDIA, QA, {}, {}, WHEN)

    def test_wrong_network_and_untrusted_media_blocked(self):
        wrong = dict(POST, providers=[{"network": "instagram"}])
        with self.assertRaises(ReleaseBlocked):
            build_update(wrong, MEDIA, QA, EVIDENCE, {}, WHEN)
        with self.assertRaises(ReleaseBlocked):
            build_update(POST, "http://untrusted.com/a.mp4", QA, EVIDENCE, {}, WHEN)

    def test_only_one_connector_dispatch_per_uuid_even_after_restart(self):
        calls = []
        def fake_adapter(**args):
            calls.append(args)
            return {"data": {"id": 443607770, "uuid": "stable-uuid",
                    "draft": False, "autoPublish": True,
                    "providers": [{"network": "tiktok"}]}}
        kw = dict(post=POST, media_url=MEDIA, job={}, qa=QA,
                  evidence=EVIDENCE, when=WHEN, update_post=fake_adapter)
        r1 = dispatch(self.ledger, **kw)
        self.assertEqual(r1["status"], "SCHEDULED")
        self.assertEqual(len(calls), 1)
        self.ledger.db.close()
        self.ledger = ReleaseLedger(Path(self.temp.name)/"queue.sqlite")
        r2 = dispatch(self.ledger, **kw)
        self.assertTrue(r2["duplicate_avoided"])
        self.assertEqual(len(calls), 1)

    def test_ambiguous_timeout_requires_reconciliation(self):
        def bad(**args):
            raise TimeoutError("unknown")
        with self.assertRaises(TimeoutError):
            dispatch(self.ledger, post=POST, media_url=MEDIA, job={},
                     qa=QA, evidence=EVIDENCE, when=WHEN, update_post=bad)
        self.assertEqual(self.ledger.claim("stable-uuid", SHA)["status"],
                         "RECONCILE_REQUIRED")

    def test_metricool_receipt_is_not_a_public_tiktok_url(self):
        def fake(**args):
            return {"data": {"id": 443607770, "uuid": "stable-uuid",
                    "draft": False, "autoPublish": True,
                    "providers": [{"network": "tiktok"}]}}
        result = dispatch(self.ledger, post=POST, media_url=MEDIA, job={},
                          qa=QA, evidence=EVIDENCE, when=WHEN, update_post=fake)
        self.assertEqual(result["status"], "SCHEDULED")
        self.assertIsNone(result["public_url"])
        with self.assertRaises(ReleaseBlocked):
            self.ledger.published("stable-uuid", "https://example.org/video/123")


if __name__ == "__main__":
    unittest.main()
