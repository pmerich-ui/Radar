import unittest
from PIL import Image
from src.producer import CATALOG
from src.visuals import frame, product_kind

class VisualStoryboardTests(unittest.TestCase):
    def test_visual_categories(self):
        self.assertEqual(product_kind("Beauty-Gadget"), "beauty")
        self.assertEqual(product_kind("Küchen-Gadget"), "kitchen")
        self.assertEqual(product_kind("Unboxing"), "parcel")
        self.assertEqual(product_kind("Preisvergleich"), "tag")
    def test_three_scenes_are_distinct(self):
        frames=[]
        for stage in range(3):
            image=Image.new("RGB",(720,1280))
            frame(image,CATALOG[0],stage,42)
            self.assertEqual(image.size,(720,1280))
            frames.append(image.tobytes())
        self.assertEqual(len(set(frames)),3)

if __name__ == "__main__":
    unittest.main()
