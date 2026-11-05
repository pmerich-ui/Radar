import unittest
from datetime import datetime, timedelta, timezone
from src.price_adapter import validate_price_payload

class PriceAdapterTests(unittest.TestCase):
    def test_requires_demo_mode(self):
        with self.assertRaises(ValueError):
            validate_price_payload({"id":"demo-x"},demo=False)
    def test_requires_ten_observations(self):
        now=datetime.now(timezone.utc)
        history=[[(now-timedelta(days=i)).date().isoformat(),100+i] for i in range(9)]
        with self.assertRaises(ValueError):
            validate_price_payload({"id":"demo-x","currency":"CHF","current_price":90,"history":history},demo=True)
    def test_valid_demo(self):
        now=datetime.now(timezone.utc)
        history=[[(now-timedelta(days=i)).date().isoformat(),100+i] for i in range(10)]
        result=validate_price_payload({"id":"demo-x","currency":"CHF","current_price":90,"history":history},demo=True)
        self.assertEqual(result["median_90d_chf"],104.5)

    def test_duplicate_dates_rejected(self):
        now=datetime.now(timezone.utc)
        history=[[(now-timedelta(days=i)).date().isoformat(),100+i] for i in range(10)]
        history[9][0]=history[0][0]
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            validate_price_payload({"id":"demo-x","currency":"CHF","current_price":90,"history":history},demo=True)

if __name__=="__main__":unittest.main()
