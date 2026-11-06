"""Offline security tests for scheduled Awin feed downloader."""
import gzip
import pathlib
import tempfile
import unittest
from unittest.mock import patch
from src import awin_feed_fetch

class Response:
    status = 200
    def __init__(self, payload):
        self.payload = payload
        self.offset = 0
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, n):
        part = self.payload[self.offset:self.offset+n]
        self.offset += len(part)
        return part

class FakeOpener:
    def __init__(self, payload):
        self.payload = payload
    def open(self, request, timeout):
        return Response(self.payload)

class TestAwinFetch(unittest.TestCase):
    def test_only_awin_https_domain(self):
        valid = "https://productdata.awin.com/datafeed/download/apikey/REDACTED"
        self.assertEqual(awin_feed_fetch.validate_url(valid), valid)
        for url in ("http://productdata.awin.com/datafeed", "https://evil.com/x",
                    "https://productdata.awin.com.evil.com/x",
                    "https://productdata.awin.com@evil.com/x",
                    "https://productdata.awin.com:8443/x",
                    "file:///etc/passwd", "https://productdata.awin.com/#frag"):
            with self.assertRaises(ValueError, msg=url):
                awin_feed_fetch.validate_url(url)

    def test_valid_gzip_is_audited_and_deleted(self):
        data = ("merchant_id,merchant_name,currency,last_updated,delivery_cost,product_name,search_price,aw_deep_link,merchant_product_id\n"
                "1,Test,CHF,2026-11-06,0,Item,15,https://www.awin1.com/test,SKU1\n")
        payload = gzip.compress(data.encode("utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with patch.object(awin_feed_fetch, "build_opener", return_value=FakeOpener(payload)):
                result = awin_feed_fetch.download_and_audit(
                    "https://productdata.awin.com/feed", root=root)
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["audit"]["total_rows"], 1)
            self.assertEqual(result["publishable_deals"], 0)
            self.assertFalse((root / "data/awin/incoming/scheduled.csv.gz").exists())

    def test_bad_gzip_rejected_without_residual_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with patch.object(awin_feed_fetch, "build_opener", return_value=FakeOpener(b"not gzip")):
                with self.assertRaises(OSError):
                    awin_feed_fetch.download_and_audit("https://productdata.awin.com/feed", root=root)
            self.assertFalse((root / "data/awin/incoming/scheduled.csv.gz").exists())

if __name__ == "__main__":
    unittest.main()
