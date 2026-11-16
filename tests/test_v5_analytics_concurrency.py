"""POSIX interprocess regression: concurrent 24h snapshots must not lose updates."""
import json
import multiprocessing
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.v5_analytics import record_once


def _capture(path, video_id, start, result_queue):
    try:
        captured = start + timedelta(hours=25)
        result_queue.put((video_id, record_once(path, video_id, start, captured, {"views": 1})))
    except Exception as exc:
        result_queue.put((video_id, type(exc).__name__ + ": " + str(exc)))


class AnalyticsConcurrentWritesTests(unittest.TestCase):
    def test_parallel_distinct_video_ids_are_all_persisted(self):
        ctx = multiprocessing.get_context("spawn")
        published = datetime(2026, 11, 14, 18, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "24h.json")
            results = ctx.Queue()
            processes = [
                ctx.Process(target=_capture, args=(path, "public-" + str(i), published, results))
                for i in range(6)
            ]
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=20)
                if process.is_alive():
                    process.terminate()
                    process.join()
                    self.fail("Concurrent writer exceeded timeout")
                self.assertEqual(process.exitcode, 0)
            outcomes = [results.get(timeout=3) for _ in processes]
            self.assertTrue(all(outcome is True for _, outcome in outcomes), outcomes)
            snapshots = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(set(snapshots), {"public-" + str(i) for i in range(6)})

    def test_parallel_same_video_id_records_once(self):
        ctx = multiprocessing.get_context("spawn")
        published = datetime(2026, 11, 14, 18, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "24h.json")
            results = ctx.Queue()
            processes = [
                ctx.Process(target=_capture, args=(path, "same-public-video", published, results))
                for _ in range(5)
            ]
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=20)
                if process.is_alive():
                    process.terminate()
                    process.join()
                    self.fail("Concurrent writer exceeded timeout")
                self.assertEqual(process.exitcode, 0)
            outcomes = [results.get(timeout=3)[1] for _ in processes]
            self.assertEqual(outcomes.count(True), 1, outcomes)
            self.assertEqual(outcomes.count(False), 4, outcomes)
            snapshots = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(list(snapshots), ["same-public-video"])


if __name__ == "__main__":
    unittest.main()
