"""Offline tests for the DealRadar fail-closed queue worker."""
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
from src import agent_queue

class TestQueue(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.patcher = patch.object(agent_queue, "QUEUE", pathlib.Path(self.temp.name))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_round_trip_no_publication(self):
        item = agent_queue.enqueue("01", "trial-001", "Review status only")
        self.assertEqual(item["state"], "PENDING")
        receipts = agent_queue.process()
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["status"], "NEEDS_REVIEW")
        self.assertFalse(receipts[0]["published"])
        self.assertFalse(receipts[0]["external_mutation"])
        self.assertFalse((agent_queue.QUEUE / "pending" / "trial-001.json").exists())
        self.assertEqual(agent_queue.process(), [])

    def test_deduplication(self):
        agent_queue.enqueue("02", "unique-1", "Inspect task queue")
        with self.assertRaises(ValueError):
            agent_queue.enqueue("02", "unique-1", "Again")
        agent_queue.process()
        with self.assertRaises(ValueError):
            agent_queue.enqueue("02", "unique-1", "Again")

    def test_unauthorized_agent_and_path(self):
        for agent, task in [("99", "test1"), ("01", "../escape"), ("xx", "ok")]:
            with self.assertRaises(ValueError):
                agent_queue.enqueue(agent, task, "Inspect")

    def test_independent_qa_blocks_without_evidence(self):
        agent_queue.enqueue("21", "qa-missing", "Publish without frames")
        receipt = agent_queue.process()[0]
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertIn("QA", receipt["reason"])

    def test_publisher_never_posts(self):
        agent_queue.enqueue("24", "publish-attempt", "Publish this now")
        receipt = agent_queue.process()[0]
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertFalse(receipt["published"])

    def test_malformed_queue_item_is_not_executed(self):
        path = agent_queue.QUEUE / "pending" / "bad.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"task_id": "other", "agent_id": "01"}))
        with self.assertRaises(ValueError):
            agent_queue.process()
        self.assertTrue(path.exists())

if __name__ == "__main__":
    unittest.main()
