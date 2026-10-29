"""Tao du lieu ban dau cho ung dung web (DE_TAI.md muc 12, F2). Chay nhieu lan khong sao (khong tao trung).

  1. Tai khoan quan tri: ADMIN_USERNAME / ADMIN_PASSWORD trong .env (mat khau doi trong .env thi chay lai de cap nhat).
  2. 1 cong: nguon hinh + vung kiem tra. Vung lay tu configs/gates.yaml (--zone ten_cong, vd cong_dt) hoac ca khung hinh.
  3. Ca mac dinh (attendance.default_shift trong settings.yaml): 07:00-17:00, nghi 60, an han 5, vao som 60 phut.
  4. 2 to doi mau (chi tao khi chua co to doi nao).
  5. (tuy chon) --faces <thu_muc>: nhap mau khuon mat tu <thu_muc>/<ma_cong_nhan>/*.jpg cho cong nhan DA CO trong CSDL
     (dung lai src/face/enroll.py). Cong nhan chua ghi nhan dong y thi bo qua, tru khi them --dong-y (xac nhan da co
     giay dong y cua cac cong nhan do; ghi consent_at, consent_by = admin).

Chay:
  .venv\\Scripts\\python.exe scripts\\seed_demo.py
  .venv\\Scripts\\python.exe scripts\\seed_demo.py --source 0                       (doi nguon hinh cua cong)
  .venv\\Scripts\\python.exe scripts\\seed_demo.py --source http://192.168.1.10:4747/video --zone cong_dt
  .venv\\Scripts\\python.exe scripts\\seed_demo.py --source data\\raw\\cong_gia_v1\\du_do_01.mp4 --zone cong_gia_v1
  .venv\\Scripts\\python.exe scripts\\seed_demo.py --faces data\\anh_dang_ky --dong-y
URL camera co mat khau: KHONG luu vao CSDL, dat GATE_SOURCE trong .env.
"""
import argparse
import sys
from datetime import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app.auth import hash_password, verify_password
from app.config import load_app_config, mask_source
from app.db import Database
from app.main import enroll_models
from app.models import Gate, Shift, Team, User, Worker
from app.services.dang_ky_mat import UPLOAD, DangKyMat, DangKyMatError
from app.services.nhan_dien import NhanDien
from src.face.enroll import best_samples, enroll_folder
from src.zone.zone import choose_rotate, load_gate

FULL_FRAME = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
DEMO_TEAMS = [
    {"name": "Tổ cốp pha", "contractor": "Nhà thầu phụ A", "leader_name": "Tổ trưởng cốp pha"},
    {"name": "Tổ cốt thép", "contractor": "Nhà thầu phụ B", "leader_name": "Tổ trưởng cốt thép"},
]


def parse_hhmm(s: str) -> time:
    h, m = str(s).split(":")
    return time(int(h), int(m))


def seed_admin(db, cfg) -> User:
    if not cfg.admin_password:
        sys.exit("Loi: chua dat ADMIN_PASSWORD trong .env (xem .env.example)")
    user = db.scalar(select(User).where(User.username == cfg.admin_username))
    if user is None:
        user = User(username=cfg.admin_username, password_hash=hash_password(cfg.admin_password),
                    full_name="Quản trị viên", role="admin", is_active=True)
        db.add(user)
        print(f"Tao tai khoan quan tri: {cfg.admin_username}")
    elif not verify_password(cfg.admin_password, user.password_hash):
        user.password_hash = hash_password(cfg.admin_password)
        print(f"Cap nhat mat khau tai khoan {cfg.admin_username} theo .env")
    else:
        print(f"Tai khoan quan tri {cfg.admin_username}: da co")
    db.commit()
    return user


def seed_gate(db, settings, args) -> Gate:
    gate = db.scalar(select(Gate).order_by(Gate.id).limit(1))
    changing = gate is None or any(v is not None for v in (args.source, args.zone, args.rotate))
    if not changing:
        print(f"Cong '{gate.name}': da co (nguon {mask_source(gate.camera_source)}), giu nguyen")
        return gate
    source = args.source if args.source is not None else (gate.camera_source if gate else str(settings["gate"]["source"]))
    if "@" in source and "://" in source:
        sys.exit("Loi: URL camera co mat khau -> dat GATE_SOURCE trong .env, khong luu vao CSDL")
    zone_name = args.zone if args.zone is not None else (None if gate else settings["gate"]["zone_name"])
    if zone_name:
        try:
            entry = load_gate(settings["paths"]["gates_file"], zone_name)
            rotate = choose_rotate(args.rotate, entry, 0)
        except (KeyError, ValueError) as e:
            sys.exit(f"Loi: {e}")
        zone = entry["zone"]
    elif gate is not None and args.zone is None:
        zone, rotate = gate.zone, args.rotate if args.rotate is not None else gate.rotate
    else:
        zone, rotate = FULL_FRAME, args.rotate if args.rotate is not None else settings["camera"]["rotate"]
    if gate is None:
        gate = Gate(name="Cổng chính", camera_source=source, zone=zone, rotate=rotate, required_ppe=None)
        db.add(gate)
        print("Tao cong 'Cổng chính'")
    else:
        gate.camera_source, gate.zone, gate.rotate = source, zone, rotate
        print(f"Cap nhat cong '{gate.name}'")
    db.commit()
    print(f"   nguon hinh: {mask_source(source)} | vung: {zone_name or ('ca khung hinh' if zone == FULL_FRAME else 'giu nguyen')}"
          f" | xoay {rotate} do")
    return gate


def seed_shift(db, settings) -> Shift:
    shift = db.scalar(select(Shift).order_by(Shift.id).limit(1))
    if shift is not None:
        print(f"Ca '{shift.name}': da co ({shift.start_time:%H:%M}-{shift.end_time:%H:%M})")
        return shift
    d = settings["attendance"]["default_shift"]
    shift = Shift(name=d["name"], start_time=parse_hhmm(d["start"]), end_time=parse_hhmm(d["end"]),
                  break_minutes=d["break_minutes"], grace_minutes=d["grace_minutes"],
                  early_checkin_minutes=d["early_checkin_minutes"], is_overnight=False, is_overtime=False)
    db.add(shift)
    db.commit()
    print(f"Tao ca '{shift.name}' {d['start']}-{d['end']}, nghi {d['break_minutes']}, an han {d['grace_minutes']}, "
          f"vao som {d['early_checkin_minutes']} phut")
    return shift


def seed_teams(db) -> None:
    if db.scalar(select(func.count(Team.id))):
        print("To doi: da co, giu nguyen")
        return
    for t in DEMO_TEAMS:
        db.add(Team(**t))
    db.commit()
    print(f"Tao {len(DEMO_TEAMS)} to doi mau: {', '.join(t['name'] for t in DEMO_TEAMS)}")


def import_faces(db, settings, admin: User, folder: Path, consent: bool) -> None:
    if not folder.is_dir():
        sys.exit(f"Loi: khong thay thu muc anh {folder}")
    nhan_dien = NhanDien(settings["face"])
    dang_ky = DangKyMat(settings, settings["paths"]["face_samples"], nhan_dien, lambda: enroll_models(settings["face"]))
    fd, emb = enroll_models(settings["face"])
    samples, notes = enroll_folder(folder, fd, emb, settings["face"])
    for line in notes:
        print(f"   {line}")
    for code, lst in samples.items():
        worker = db.scalar(select(Worker).where(Worker.code == code))
        if worker is None:
            print(f"   {code}: khong co cong nhan ma nay trong CSDL, bo qua (tao cong nhan truoc)")
            continue
        if worker.consent_at is None:
            if not consent:
                print(f"   {code}: chua ghi nhan dong y, bo qua (ghi nhan qua API, hoac chay lai voi --dong-y)")
                continue
            dang_ky.ghi_nhan_dong_y(db, worker, admin)
        added = 0
        for s in best_samples(lst, settings["face"]["max_samples"]):
            try:
                dang_ky.luu_mau(db, worker, s, UPLOAD)
                added += 1
            except DangKyMatError as e:
                print(f"   {code}: {e}")
                break
        print(f"   {code} ({worker.full_name}): them {added} mau, tong {dang_ky.so_mau(db, worker)}")


def main():
    cfg = load_app_config()
    settings = cfg.settings
    parser = argparse.ArgumentParser(description="Tao tai khoan quan tri, cong, ca, to doi mau; nhap mau khuon mat.")
    parser.add_argument("--source", default=None, help="Nguon hinh cua cong: so webcam, URL, file video.")
    parser.add_argument("--zone", default=None, help="Ten vung trong configs/gates.yaml; 'ca_khung' = ca khung hinh.")
    parser.add_argument("--rotate", type=int, choices=[0, 90, 180, 270], default=None)
    parser.add_argument("--faces", type=Path, default=None, help="Thu muc anh <ma_cong_nhan>/*.jpg.")
    parser.add_argument("--dong-y", action="store_true",
                        help="Xac nhan da co giay dong y cua cac cong nhan trong --faces (ghi nhan dong y khi nhap).")
    args = parser.parse_args()
    if args.zone == "ca_khung":
        args.zone = ""

    db = Database(cfg.database_url)
    db.create_all()
    print(f"CSDL: {db.kind}")
    with db.session() as s:
        admin = seed_admin(s, cfg)
        seed_gate(s, settings, args)
        seed_shift(s, settings)
        seed_teams(s)
        if args.faces is not None:
            print(f"Nhap mau khuon mat tu {args.faces}:")
            import_faces(s, settings, admin, args.faces, args.dong_y)
    print("Xong. Chay ung dung:  .venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000")


if __name__ == "__main__":
    main()
