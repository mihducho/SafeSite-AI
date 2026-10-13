"""Test logic gan PPE cho nguoi. Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ppe.compliance import HEAD_REGION, TORSO_REGION, PPERule, assign_ppe, missing_ppe

PERSON, HARDHAT, VEST = 5, 0, 6
RULES = [PPERule("hardhat", HARDHAT, HEAD_REGION), PPERule("vest", VEST, TORSO_REGION)]

# Nguoi cao 300px, rong 100px. Non nho (~3% dien tich box nguoi) o dinh dau,
# ao o giua than — dung ti le thuc te tren video.
PERSON_BOX = [100, 100, 200, 400]
HAT_ON_HEAD = [130, 90, 170, 120]
VEST_ON_TORSO = [110, 160, 190, 280]


def run(persons, dets):
    """dets: list (xyxy, cls). Tra ve ket qua assign_ppe."""
    det_xyxy = [d[0] for d in dets]
    det_cls = [d[1] for d in dets]
    return assign_ppe(np.array(persons), np.array(det_xyxy), np.array(det_cls), RULES)


class AssignPPETest(unittest.TestCase):
    def test_small_hardhat_on_head_counts(self):
        # Truoc day chia theo dien tich box nguoi -> non nho luon bi tinh la thieu.
        status = run([PERSON_BOX], [(HAT_ON_HEAD, HARDHAT), (VEST_ON_TORSO, VEST)])
        self.assertEqual(status, [{"hardhat": True, "vest": True}])

    def test_no_ppe_detected(self):
        status = run([PERSON_BOX], [])
        self.assertEqual(missing_ppe(status[0]), ["hardhat", "vest"])

    def test_hardhat_at_feet_does_not_count(self):
        # Non cam tay / de duoi dat: nam trong box nguoi nhung khong o vung dau.
        hat_at_feet = [130, 360, 170, 390]
        status = run([PERSON_BOX], [(hat_at_feet, HARDHAT)])
        self.assertFalse(status[0]["hardhat"])

    def test_vest_on_head_region_does_not_count_as_hardhat(self):
        status = run([PERSON_BOX], [(HAT_ON_HEAD, VEST)])
        self.assertFalse(status[0]["hardhat"])

    def test_hardhat_goes_to_one_person_only(self):
        # 2 nguoi dung sat nhau, non nam vat qua vung dau ca 2 (>50% trong moi
        # vung) nhung nghieng ve nguoi ben trai -> chi nguoi ben trai duoc tinh.
        left = [100, 100, 200, 400]
        right = [180, 100, 280, 400]
        shared_hat = [165, 90, 205, 120]
        status = run([left, right], [(shared_hat, HARDHAT)])
        self.assertTrue(status[0]["hardhat"])
        self.assertFalse(status[1]["hardhat"])

    def test_two_people_each_with_hardhat(self):
        left = [100, 100, 200, 400]
        right = [300, 100, 400, 400]
        right_hat = [330, 90, 370, 120]
        status = run([left, right], [(HAT_ON_HEAD, HARDHAT), (right_hat, HARDHAT)])
        self.assertEqual([s["hardhat"] for s in status], [True, True])

    def test_no_person(self):
        self.assertEqual(run(np.zeros((0, 4)), [(HAT_ON_HEAD, HARDHAT)]), [])

    def test_degenerate_ppe_box_ignored(self):
        status = run([PERSON_BOX], [([150, 100, 150, 100], HARDHAT)])
        self.assertFalse(status[0]["hardhat"])


if __name__ == "__main__":
    unittest.main()
