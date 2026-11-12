#!/usr/bin/env python3
"""Offline regression tests for 24h analytics persistence."""
import tempfile, unittest
from pathlib import Path
from analytics_24h import record

class LedgerTests(unittest.TestCase):
    def test_due_idempotent_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            db=str(Path(d)/"ledger.sqlite")
            pub="2026-11-10T18:00:00+01:00"
            early=record(db,"video1",pub,"2026-11-11T17:59:59+01:00",{"TKPO07":8})
            self.assertEqual(early["status"],"NOT_DUE")
            due=record(db,"video1",pub,"2026-11-11T18:10:00+01:00",{"TKPO07":8})
            self.assertEqual(due["status"],"RECORDED")
            self.assertIn("TKPO13",due["missing"])
            again=record(db,"video1",pub,"2026-11-12T18:10:00+01:00",{"TKPO07":100})
            self.assertEqual(again["status"],"ALREADY_RECORDED")
    def test_no_metrics_no_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            db=str(Path(d)/"a.sqlite")
            r=record(db,"v2","2026-11-10T18:00:00Z","2026-11-12T18:00:00Z",{})
            self.assertEqual(r["status"],"DATA_UNAVAILABLE")
            r=record(db,"v2","2026-11-10T18:00:00Z","2026-11-12T18:00:00Z",{"TKPO08":0})
            self.assertEqual(r["status"],"RECORDED")
    def test_naive_timestamp_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                record(str(Path(d)/"a.sqlite"),"v","2026-11-10T18:00:00","2026-11-12T18:00:00Z",{})
if __name__=="__main__": unittest.main()
