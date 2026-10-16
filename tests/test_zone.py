"""Test kiem tra vung nguy hiem. Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.zone.zone import load_zones, person_feet_point, point_in_zone, zone_to_pixels

ZONE_YAML = """
camera_1:
  - [100, 400]
  - [500, 400]
  - [500, 600]
  - [100, 600]
"""


class ZoneTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
        tmp.write(ZONE_YAML)
        tmp.close()
        self.path = Path(tmp.name)
        self.zone = load_zones(self.path)["camera_1"]

    def tearDown(self):
        self.path.unlink()

    def test_feet_inside_zone(self):
        # Nguoi dung trong vung: chan (y=500) nam trong vung du dau nam ngoai.
        self.assertTrue(point_in_zone(person_feet_point([250, 200, 350, 500]), self.zone))

    def test_body_overlaps_but_feet_outside(self):
        # Box nguoi chong len vung nhung chan van ngoai vung -> khong tinh xam nhap.
        self.assertFalse(point_in_zone(person_feet_point([250, 100, 350, 390]), self.zone))

    def test_missing_file_returns_empty(self):
        self.assertEqual(load_zones(self.path.with_name("khong_ton_tai.yaml")), {})

    def test_comment_only_file_returns_empty(self):
        self.path.write_text("# chi co comment\n", encoding="utf-8")
        self.assertEqual(load_zones(self.path), {})


class ZoneToPixelsTest(unittest.TestCase):
    RATIO = [[0.25, 0.5], [0.75, 0.5], [0.75, 1.0], [0.25, 1.0]]

    def test_convert_by_frame_size(self):
        self.assertEqual(zone_to_pixels(self.RATIO, 1280, 720).tolist(), [[320, 360], [960, 360], [960, 720], [320, 720]])

    def test_same_zone_other_resolution(self):
        # Cung 1 vung ti le dung duoc cho camera do phan giai khac.
        self.assertEqual(zone_to_pixels(self.RATIO, 640, 480).tolist(), [[160, 240], [480, 240], [480, 480], [160, 480]])

    def test_pixel_coordinates_rejected(self):
        with self.assertRaises(ValueError):
            zone_to_pixels([[100, 400], [500, 400], [500, 600]], 1280, 720)

    def test_too_few_points(self):
        with self.assertRaises(ValueError):
            zone_to_pixels([[0.1, 0.1], [0.5, 0.5]], 1280, 720)


if __name__ == "__main__":
    unittest.main()
