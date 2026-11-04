import unittest
from datetime import datetime, timezone, timedelta
from src.revenue_quality import verified_offer, commission_summary

class RevenueQualityTests(unittest.TestCase):
    def offer(self):
        return dict(id="a",title="Example",merchant="Example",url="https://example.com/p",
                    price_chf=70,reference_price_chf=100,
                    verified_at=datetime.now(timezone.utc).isoformat(),
                    reference_source="independent observation",
                    reference_checked=True,stock_confirmed=True)
    def test_verified_offer_is_review_only(self):
        self.assertEqual(verified_offer(self.offer())[1],"eligible_for_editorial_review")
    def test_unverified_stock_is_rejected(self):
        offer=self.offer();offer["stock_confirmed"]=False
        self.assertFalse(verified_offer(offer)[0])
    def test_stale_offer_is_rejected(self):
        offer=self.offer();offer["verified_at"]=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
        self.assertFalse(verified_offer(offer)[0])
    def test_forged_price_is_rejected(self):
        offer=self.offer();offer["price_chf"]="NaN"
        self.assertFalse(verified_offer(offer)[0])
    def test_commissions_only_confirmed_and_separate_currency(self):
        rows=[dict(status="pending",currency="CHF",commission="100"),
              dict(status="confirmed",currency="CHF",commission="2.50"),
              dict(status="paid",currency="EUR",commission="3.25")]
        self.assertEqual(commission_summary(rows),{"CHF":"2.50","EUR":"3.25"})

if __name__=="__main__":unittest.main()
