import tempfile
import unittest
from pathlib import Path
from src.click_receiver import store_event

class ClickReceiverTests(unittest.TestCase):
    def test_persists_valid_click(self):
        with tempfile.TemporaryDirectory() as d:
            store_event({"type":"offer_click","offer_id":"sku-1","video_id":"v-1"}, d)
            self.assertTrue((Path(d)/"dealradar_events.sqlite").exists())
    def test_rejects_missing_offer(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                store_event({"type":"offer_click","offer_id":""}, d)
    def test_no_unconfigured_storage(self):
        with self.assertRaises(ValueError):
            store_event({"type":"offer_click","offer_id":"sku-1"}, "/path/that/does/not/exist")
