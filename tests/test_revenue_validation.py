import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from src.revenue_validation import audit

class RevenueValidationTests(unittest.TestCase):
    def test_empty_deals_do_not_imply_zero_revenue(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "deals.json"
            path.write_text('{"offers":[]}')
            r = audit(path)
            self.assertEqual(r["status"], "NOT_VALIDATED")
            self.assertIsNone(r["confirmed_commission_chf"])
            self.assertIn("NO_VERIFIED_OFFERS", r["blockers"])

    def test_deduplicated_confirmed_commissions(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            deals = root / "deals.json"
            deals.write_text(json.dumps({"offers":[{"status":"verified","title":"Test",
                "url":"https://example.org/item","price_chf":10,"verified_at":"2026-11-22T00:00:00Z"}]}))
            db = root / "events.sqlite"
            with sqlite3.connect(db) as con:
                con.execute("CREATE TABLE click_events(id INTEGER)")
                con.execute("INSERT INTO click_events VALUES(1)")
            commissions = root / "commissions.json"
            commissions.write_text(json.dumps({"transactions":[
                {"transaction_id":"a","status":"confirmed","commission_chf":2.5},
                {"transaction_id":"b","status":"pending","commission_chf":9}]}))
            r = audit(deals, db, commissions)
            self.assertEqual(r["status"], "MEASUREMENT_READY")
            self.assertEqual(r["tracked_clicks"], 1)
            self.assertEqual(r["confirmed_sales"], 1)
            self.assertEqual(r["confirmed_commission_chf"], 2.5)
            commissions.write_text(json.dumps({"transactions":[
                {"transaction_id":"a","status":"confirmed","commission_chf":2.5},
                {"transaction_id":"a","status":"confirmed","commission_chf":2.5}]}))
            self.assertIn("COMMISSIONS_INVALID", audit(deals, db, commissions)["blockers"])

if __name__ == "__main__":
    unittest.main()
