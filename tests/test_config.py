"""Test doc cau hinh, tra lop theo ten, tao luat PPE tu cau hinh.
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import DEFAULT_SETTINGS, load_settings
from src.detection.detect import find_class_ids
from src.ppe.compliance import rules_from_config

MODEL_NAMES = {0: "Mask", 1: "Safety-Vest", 2: "NO-Safety-Vest", 3: "Person", 4: "machinery",
               5: "Safety-Cone", 6: "vehicle", 7: "Hardhat", 8: "NO-Mask", 9: "NO-Hardhat"}


def write_settings(tmp: str, data: dict) -> Path:
    path = Path(tmp) / "settings.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


class LoadSettingsTest(unittest.TestCase):
    def test_project_settings_load(self):
        s = load_settings()
        self.assertEqual(s["model"]["person_class"], "Person")
        # Duong dan tuong doi duoc doi thanh tuyet doi theo thu muc goc du an.
        self.assertEqual(s["model"]["weights"], ROOT / "weights" / "ppe_s" / "weights" / "best.pt")
        self.assertTrue(s["paths"]["snapshot_dir"].is_absolute())

    def test_missing_key_reported(self):
        data = yaml.safe_load(DEFAULT_SETTINGS.read_text(encoding="utf-8"))
        del data["checkpoint"]["present_ratio"]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(KeyError, "checkpoint.present_ratio"):
                load_settings(write_settings(tmp, data))

    def test_required_item_must_be_declared(self):
        data = yaml.safe_load(DEFAULT_SETTINGS.read_text(encoding="utf-8"))
        data["ppe"]["required"] = ["hardhat", "gang_tay"]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(KeyError, "gang_tay"):
                load_settings(write_settings(tmp, data))

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_settings(ROOT / "configs" / "khong_ton_tai.yaml")


class FindClassIdsTest(unittest.TestCase):
    def test_lookup_by_name(self):
        ids = find_class_ids(MODEL_NAMES, ["Person", "Hardhat", "Safety-Vest"])
        self.assertEqual(ids, {"Person": 3, "Hardhat": 7, "Safety-Vest": 1})

    def test_other_model_order(self):
        # Model 3 lop sau nay: thu tu khac van tra dung.
        ids = find_class_ids({0: "Hardhat", 1: "Person", 2: "Safety-Vest"}, ["Person", "Hardhat"])
        self.assertEqual(ids, {"Person": 1, "Hardhat": 0})

    def test_missing_class_raises_with_available_list(self):
        with self.assertRaises(ValueError) as ctx:
            find_class_ids({0: "person", 1: "car"}, ["Person", "Hardhat"])
        self.assertIn("Hardhat", str(ctx.exception))
        self.assertIn("car", str(ctx.exception))  # liet ke lop cua model de de sua


class RulesFromConfigTest(unittest.TestCase):
    def setUp(self):
        self.ppe = load_settings()["ppe"]
        self.ids = find_class_ids(MODEL_NAMES, ["Hardhat", "Safety-Vest"])

    def test_rules_follow_config(self):
        rules = rules_from_config(self.ppe, self.ids)
        self.assertEqual([r.name for r in rules], self.ppe["required"])
        hardhat = next(r for r in rules if r.name == "hardhat")
        self.assertEqual(hardhat.cls_id, 7)
        self.assertEqual(hardhat.region, tuple(self.ppe["items"]["hardhat"]["region"]))

    def test_required_override(self):
        # Tat kiem tra ao (DE_TAI muc 6: danh sach do bao ho cau hinh duoc).
        rules = rules_from_config(self.ppe, self.ids, required=["hardhat"])
        self.assertEqual([r.name for r in rules], ["hardhat"])


if __name__ == "__main__":
    unittest.main()
