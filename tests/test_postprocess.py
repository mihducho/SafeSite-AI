"""Test loc box nguoi trung lap. Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.postprocess import suppress_contained


class SuppressContainedTest(unittest.TestCase):
    def test_box_inside_bigger_box_removed(self):
        # Truong hop thuc te (test6, nguoi dang cui): 1 box ca nguoi + 1 box nho gan tron ben trong.
        big = [370, 220, 700, 540]
        small = [380, 285, 570, 540]
        self.assertEqual(suppress_contained([big, small]).tolist(), [True, False])

    def test_order_does_not_matter(self):
        big, small = [370, 220, 700, 540], [380, 285, 570, 540]
        self.assertEqual(suppress_contained([small, big]).tolist(), [False, True])

    def test_two_people_side_by_side_kept(self):
        self.assertEqual(suppress_contained([[100, 100, 200, 400], [180, 100, 280, 400]]).tolist(), [True, True])

    def test_partly_occluded_person_behind_kept(self):
        # Nguoi dung sau, chi ~60% box nam trong box nguoi phia truoc -> giu.
        front = [100, 100, 300, 500]
        behind = [220, 80, 350, 400]
        self.assertEqual(suppress_contained([front, behind]).tolist(), [True, True])

    def test_identical_boxes_both_kept(self):
        # Trung khit thi NMS cua YOLO da xu ly; ham nay chi bo box nho hon.
        self.assertEqual(suppress_contained([[0, 0, 10, 10], [0, 0, 10, 10]]).tolist(), [True, True])

    def test_empty(self):
        self.assertEqual(suppress_contained([]).tolist(), [])


if __name__ == "__main__":
    unittest.main()
