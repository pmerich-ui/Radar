import unittest
from src.video_qa_agent import silence_fraction

class SilenceFractionTests(unittest.TestCase):
    def test_silent_tail(self):
        self.assertAlmostEqual(silence_fraction("silence_start: 3.0", 16), 13/16)
    def test_two_intervals(self):
        log = "silence_start: 1.0\nsilence_end: 3.0 | silence_duration: 2\nsilence_start: 8.0\nsilence_end: 10.0"
        self.assertAlmostEqual(silence_fraction(log, 20), .2)
    def test_no_silence(self):
        self.assertEqual(silence_fraction("", 16), 0)
    def test_invalid_duration(self):
        self.assertEqual(silence_fraction("", 0), 1)
    def test_overlap_clamped(self):
        self.assertEqual(silence_fraction("silence_start: 0\nsilence_end: 30", 10), 1)

if __name__ == "__main__":
    unittest.main()
