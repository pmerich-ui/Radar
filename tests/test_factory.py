import unittest
from src.producer import CATALOG,render,validate
from pathlib import Path
from tempfile import TemporaryDirectory
class TestFactory(unittest.TestCase):
    def test_unique_catalog(self):self.assertEqual(len({"|".join(i) for i in CATALOG}),len(CATALOG))
    def test_mp4(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"sample.mp4"
            info=render(CATALOG[0],p)
            self.assertEqual(info["fps"],30)
            self.assertEqual((info["width"],info["height"]),(720,1280))
            self.assertTrue(p.exists())
if __name__=="__main__":unittest.main()
