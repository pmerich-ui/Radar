import unittest
from datetime import datetime, timedelta, timezone
from src.pipeline import Status, transition, verified_deal, ninety_day_median

NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
def iso(t): return t.isoformat()
class PipelineTests(unittest.TestCase):
    def test_publish_cannot_be_assumed(self):
        with self.assertRaises(ValueError):
            transition(Status.RENDERED.value, Status.PUBLISHED_CONFIRMED.value, "claimed")
        with self.assertRaises(ValueError):
            transition(Status.DRAFT_CONFIRMED.value, Status.PUBLISHED_CONFIRMED.value)
        self.assertEqual(transition(Status.DRAFT_CONFIRMED.value, Status.PUBLISHED_CONFIRMED.value, "TikTok post id"), "PUBLISHED_CONFIRMED")
    def test_verified_deal_requires_fresh_evidence(self):
        deal = dict(status="verified", url="https://shop.example/item", evidence_url="https://shop.example/proof", price_chf=39.9, verified_at=iso(NOW))
        self.assertTrue(verified_deal(deal,NOW))
        deal["verified_at"]=iso(NOW-timedelta(days=2))
        self.assertFalse(verified_deal(deal,NOW))
    def test_median_requires_history(self):
        self.assertIsNone(ninety_day_median([{"at":iso(NOW),"price_chf":10}],NOW))
        samples=[{"at":iso(NOW-timedelta(days=i)),"price_chf":float(10+i)} for i in range(10)]
        self.assertEqual(ninety_day_median(samples,NOW),14.5)

if __name__ == "__main__": unittest.main()
