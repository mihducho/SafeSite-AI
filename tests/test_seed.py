"""Test scripts/seed_demo.py: --reset (xoa sach CSDL + anh luot + anh mau mat roi tao lai), --ca (doi gio ca), tao du lieu
ban dau khong trung khi chay lai. CSDL va thu muc tam, khong dung du lieu that.
Chay: .venv\\Scripts\\python.exe -m unittest discover -s tests -v"""
import argparse
import copy
import contextlib
import io
import sys
import tempfile
import unittest
from datetime import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app_helpers import SETTINGS, add_admin, add_shift, add_worker, make_db  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app.models import Shift, Team, Worker  # noqa: E402
from scripts.seed_demo import parse_shift_hours, reset_all, seed_shift, seed_teams  # noqa: E402


class SeedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = copy.deepcopy(SETTINGS)
        for key in ("check_images", "face_samples"):
            self.settings["paths"][key] = Path(self.tmp.name) / key
            (self.settings["paths"][key] / "2026-10-29").mkdir(parents=True)
            (self.settings["paths"][key] / "2026-10-29" / "a.jpg").write_bytes(b"x")
        self.db = make_db()

    def tearDown(self):
        self.db.engine.dispose()
        self.tmp.cleanup()

    def test_reset_xoa_sach_csdl_va_anh_roi_tao_lai(self):
        with self.db.session() as s:
            add_admin(s)
            add_shift(s)
            add_worker(s, "CN001", "Nguyễn Văn An", face_index=0)
        with contextlib.redirect_stdout(io.StringIO()):
            reset_all(self.db, self.settings, ask=False)
        with self.db.session() as s:
            self.assertEqual(s.scalar(select(func.count(Worker.id))), 0)
        for key in ("check_images", "face_samples"):
            self.assertFalse(self.settings["paths"][key].exists())
        with self.db.session() as s, contextlib.redirect_stdout(io.StringIO()):
            seed_shift(s, self.settings)
            seed_teams(s)
            seed_teams(s)  # chay lai khong tao trung
            shift = s.scalar(select(Shift))
            self.assertEqual((shift.start_time, shift.end_time, shift.break_start, shift.name),
                             (time(7, 0), time(17, 0), time(11, 30), "Ca hành chính"))
            self.assertEqual(s.scalar(select(func.count(Team.id))), 2)

    def test_ca_doi_gio_bat_dau_ket_thuc(self):
        self.assertEqual(parse_shift_hours("13:00-17:30"), (time(13, 0), time(17, 30)))
        for bad in ("17:00-07:00", "7h-17h", "07:00"):
            with self.subTest(bad=bad), self.assertRaises(argparse.ArgumentTypeError):
                parse_shift_hours(bad)
        with self.db.session() as s, contextlib.redirect_stdout(io.StringIO()):
            seed_shift(s, self.settings)
            shift = seed_shift(s, self.settings, (time(13, 0), time(17, 30)))
            self.assertEqual((shift.start_time, shift.end_time), (time(13, 0), time(17, 30)))
            self.assertEqual(s.scalar(select(func.count(Shift.id))), 1)


if __name__ == "__main__":
    unittest.main()
