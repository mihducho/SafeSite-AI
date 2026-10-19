"""Test loc box nguoi trung lap. Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import load_settings
from src.utils.postprocess import suppress_contained

PPE_CFG = load_settings()["ppe"]
CONTAIN_THRESH = PPE_CFG["contain_thresh"]  # 0.8 trong configs/settings.yaml
GROUP_MAX_X_OVERLAP = PPE_CFG["group_max_x_overlap"]  # 0.5


def keep(boxes, group_max_x_overlap=GROUP_MAX_X_OVERLAP):
    return suppress_contained(boxes, contain_thresh=CONTAIN_THRESH, group_max_x_overlap=group_max_x_overlap)


class SuppressContainedTest(unittest.TestCase):
    def test_box_inside_bigger_box_removed(self):
        # Truong hop thuc te (test6, nguoi dang cui): 1 box ca nguoi + 1 box nho gan tron ben trong.
        big = [370, 220, 700, 540]
        small = [380, 285, 570, 540]
        self.assertEqual(keep([big, small]).tolist(), [True, False])

    def test_order_does_not_matter(self):
        big, small = [370, 220, 700, 540], [380, 285, 570, 540]
        self.assertEqual(keep([small, big]).tolist(), [False, True])

    def test_two_people_side_by_side_kept(self):
        self.assertEqual(keep([[100, 100, 200, 400], [180, 100, 280, 400]]).tolist(), [True, True])

    def test_partly_occluded_person_behind_kept(self):
        # Nguoi dung sau, chi ~60% box nam trong box nguoi phia truoc -> giu.
        front = [100, 100, 300, 500]
        behind = [220, 80, 350, 400]
        self.assertEqual(keep([front, behind]).tolist(), [True, True])

    def test_identical_boxes_both_kept(self):
        # Trung khit thi NMS cua YOLO da xu ly; ham nay chi bo box nho hon.
        self.assertEqual(keep([[0, 0, 10, 10], [0, 0, 10, 10]]).tolist(), [True, True])

    def test_empty(self):
        self.assertEqual(keep([]).tolist(), [])


class GroupBoxTest(unittest.TestCase):
    """Box gop: model ve them 1 box bao nhieu nguoi dung sat vai nhau."""

    # So lieu that (2026-10-20, khung 720x1280, 2 nguoi sat vai): nguoi trai, box gop, nguoi phai.
    LEFT, GROUP, RIGHT = [0, 115, 360, 845], [14, 128, 590, 1011], [310, 128, 590, 858]

    def test_group_box_removed_people_kept(self):
        self.assertEqual(keep([self.LEFT, self.GROUP, self.RIGHT]).tolist(), [True, False, True])

    def test_halves_of_one_person_not_split(self):
        # Nua tren + nua duoi cua 1 nguoi: chong nhau het chieu ngang -> khong phai 2 nguoi.
        whole, top, bottom = [100, 100, 300, 600], [100, 100, 300, 350], [105, 350, 295, 600]
        self.assertEqual(keep([whole, top, bottom]).tolist(), [True, False, False])

    def test_half_body_duplicate_still_removed(self):
        # Chi 1 box nam trong (box nua than cua chinh nguoi do) -> xu ly nhu cu.
        self.assertEqual(keep([[186, 166, 590, 1255], [186, 166, 590, 858]]).tolist(), [True, False])

    def test_group_check_off_keeps_old_behavior(self):
        self.assertEqual(keep([self.LEFT, self.GROUP, self.RIGHT], group_max_x_overlap=None).tolist(),
                         [False, True, False])


if __name__ == "__main__":
    unittest.main()
