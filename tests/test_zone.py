"""Test kiem tra vung nguy hiem. Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.zone.zone import (choose_rotate, clicks_to_ratio, load_gate, load_gate_zone, load_gates, load_zones,
                           person_feet_point, point_in_zone, save_gate_zone, zone_to_pixels)

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


class GateZoneFileTest(unittest.TestCase):
    """Doc/ghi vung ti le 0-1 trong file cong (configs/gates.yaml)."""

    ZONE = [[0.25, 0.5], [0.75, 0.5], [0.75, 1.0], [0.25, 1.0]]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "gates.yaml"

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_then_load(self):
        save_gate_zone(self.path, "cong_1", self.ZONE)
        self.assertEqual(load_gate_zone(self.path, "cong_1"), self.ZONE)

    def test_header_comment_kept(self):
        save_gate_zone(self.path, "cong_1", self.ZONE)
        save_gate_zone(self.path, "cong_1", self.ZONE)
        self.assertTrue(self.path.read_text(encoding="utf-8").startswith("# Vung kiem tra"))

    def test_other_gates_kept_and_overwrite(self):
        save_gate_zone(self.path, "cong_1", self.ZONE)
        save_gate_zone(self.path, "cong_2", [[0, 0], [1, 0], [1, 1]])
        save_gate_zone(self.path, "cong_1", [[0.1, 0.1], [0.9, 0.1], [0.5, 0.9]])
        gates = load_gates(self.path)
        self.assertEqual(set(gates), {"cong_1", "cong_2"})
        self.assertEqual(gates["cong_1"]["zone"], [[0.1, 0.1], [0.9, 0.1], [0.5, 0.9]])

    def test_pixel_coordinates_not_saved(self):
        with self.assertRaises(ValueError):
            save_gate_zone(self.path, "cong_1", [[100, 400], [500, 400], [500, 600]])
        self.assertFalse(self.path.exists())

    def test_missing_gate_lists_available(self):
        save_gate_zone(self.path, "cong_1", self.ZONE)
        with self.assertRaisesRegex(KeyError, "cong_1"):
            load_gate_zone(self.path, "cong_9")

    def test_clicks_to_ratio(self):
        # Click tren anh hien thi 1280x720 (anh 4K da thu nho): ti le khong phu thuoc do phan giai goc.
        self.assertEqual(clicks_to_ratio([[320, 360], [960, 720], [1290, -5]], 1280, 720),
                         [[0.25, 0.5], [0.75, 1.0], [1.0, 0.0]])  # click lo ra ngoai anh bi kep ve 0-1

    def test_rotate_saved_with_zone(self):
        save_gate_zone(self.path, "cong_dt", self.ZONE, rotate=90)
        self.assertEqual(load_gate(self.path, "cong_dt"), {"zone": self.ZONE, "rotate": 90})
        save_gate_zone(self.path, "cong_dt", self.ZONE)  # ve lai khong xoay -> ghi de goc cu
        self.assertEqual(load_gate(self.path, "cong_dt")["rotate"], 0)

    def test_old_entry_without_rotate_is_0(self):
        # Vung ve truoc khi co tinh nang xoay (chi co zone) van doc duoc, coi nhu khong xoay.
        self.path.write_text("cong_1:\n  zone: [[0.25, 0.5], [0.75, 0.5], [0.75, 1.0]]\n", encoding="utf-8")
        self.assertEqual(load_gate(self.path, "cong_1")["rotate"], 0)

    def test_invalid_rotate_not_saved(self):
        with self.assertRaises(ValueError):
            save_gate_zone(self.path, "cong_1", self.ZONE, rotate=45)
        self.assertFalse(self.path.exists())


class ChooseRotateTest(unittest.TestCase):
    """Goc xoay khi chay kiem tra: co cong thi theo goc luu cung vung."""

    GATE = {"zone": [[0, 0], [1, 0], [1, 1]], "rotate": 90}

    def test_gate_rotate_used_by_default(self):
        self.assertEqual(choose_rotate(None, self.GATE, default=0), 90)

    def test_cli_same_as_gate_ok(self):
        self.assertEqual(choose_rotate(90, self.GATE, default=0), 90)

    def test_cli_different_from_gate_rejected(self):
        # Vung ve tren hinh xoay 90 ma chay khong xoay -> vung lech, phai bao loi.
        with self.assertRaisesRegex(ValueError, "ve lai vung"):
            choose_rotate(0, self.GATE, default=0)

    def test_no_gate_cli_then_config(self):
        self.assertEqual(choose_rotate(270, None, default=0), 270)
        self.assertEqual(choose_rotate(None, None, default=180), 180)
        with self.assertRaises(ValueError):
            choose_rotate(None, None, default=45)


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
