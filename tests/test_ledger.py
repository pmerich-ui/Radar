import unittest
from src.save_ledger import merge


class LedgerMergeTests(unittest.TestCase):
    def test_preserves_remote_and_new_local_records(self):
        remote = [{"id": "A", "sha256": "abc"}]
        local = [{"id": "A", "sha256": "abc"}, {"id": "B", "sha256": "def"}]
        self.assertEqual([r["id"] for r in merge(remote, local)], ["A", "B"])

    def test_detects_conflicting_media_for_same_id(self):
        with self.assertRaises(ValueError):
            merge([{"id": "A", "sha256": "one"}], [{"id": "A", "sha256": "two"}])

    def test_merging_identical_ledgers_is_idempotent(self):
        items = [{"id": "X", "sha256": "xyz"}]
        self.assertEqual(merge(items, items), items)


if __name__ == "__main__":
    unittest.main()
