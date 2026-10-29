# SafeSite-AI

Đồ án tốt nghiệp: **hệ thống quản lý và chấm công công nhân tại công trường, tích hợp kiểm tra trang bị
bảo hộ lao động bằng thị giác máy tính**.

**SafeGate** (DE_TAI.md phiên bản 2): một camera tại cổng vừa **nhận diện khuôn mặt** để biết công nhân là ai
(YuNet + SFace của OpenCV), vừa kiểm tra **mũ bảo hộ và áo phản quang** (YOLO11s); đủ bảo hộ thì tự động ghi công.
Mô tả đầy đủ, phạm vi, các giai đoạn nước rút F1–F4 nằm ở [DE_TAI.md](DE_TAI.md).

## Trạng thái

- [x] Giai đoạn 0: rà soát code cũ, xem [docs/RA_SOAT.md](docs/RA_SOAT.md)
- [x] Giai đoạn 1a: dọn code hướng cũ vào `_old/`, file cấu hình chung, tra lớp theo tên, ghim thư viện
- [ ] Giai đoạn 1b: dịch vụ AI chế độ cổng
  - [x] 1b-1: `evaluate_frames` (thuật toán mục 5) + test bằng box giả
  - [x] 1b-2: luồng đọc camera, `check`, vùng kiểm tra tỷ lệ 0–1, script chạy thử; chạy thật với webcam
  - [x] Đọc được camera điện thoại qua Wi-Fi (DroidCam 1280x720: ~18 khung/lượt, ~85 ms/khung), xem
        [docs/huong_dan_camera_dien_thoai.md](docs/huong_dan_camera_dien_thoai.md)
  - [x] Chạy thử tại cổng với điện thoại dựng dọc (`--rotate 90`): đủ đồ, thiếu mũ, thiếu áo, 2 người, mũ két
  - [ ] Quay video các tình huống (dùng lại cho Giai đoạn 2); kéo mép vùng sát mép hình trong `define_zone.py` (để sau)
- [ ] Giai đoạn 2: script đánh giá trên video
  - [x] Bản rút gọn: tạo file đáp án từ tên video, đánh giá (tỷ lệ đúng, ma trận nhầm lẫn, precision/recall
        vi phạm, KHONG_XAC_DINH, thời gian), so sánh imgsz 640/960
  - [x] Chạy trên bộ video tự quay `cong_gia_v1` (43 video, imgsz 640: 38/43 đúng, precision vi phạm 100%,
        recall 90.9%), xem [docs/ket_qua_danh_gia_cong_v1.md](docs/ket_qua_danh_gia_cong_v1.md)
  - [ ] Mở rộng bộ video (ngược sáng, thiếu sáng, mũ vải...), hiệu chỉnh ngưỡng
- [x] **F1. Khuôn mặt + vòng lặp cổng (phần AI)**: `src/face/` (YuNet, SFace, gắn mặt với người trong vùng, đếm mặt,
      so khớp), `src/gate/` (kết hợp + luật `nhieu_mat`, máy trạng thái, một lượt, vòng lặp cổng), đăng ký mẫu,
      `run_gate.py`, `evaluate_faces.py`. Bộ `cong_gia_v1` (cùng 18 khung): bảo hộ 38/43 → 40/43 sau luật `nhieu_mat`
- [x] **F2. Backend + CSDL**: ứng dụng FastAPI `app/` (SQLAlchemy 2: SQLite hoặc PostgreSQL), đăng nhập, API JSON
      (công nhân, tổ đội, mẫu mặt, lượt kiểm tra, bảng công, chấm công thủ công, tổng quan), WebSocket `/ws/events`,
      luồng hình `/stream/gate`, vòng lặp cổng chạy nền trong ứng dụng, `scripts/seed_demo.py`
- [ ] F3. Giao diện web · F4. Đánh giá `cong_gia_v2` + hoàn thiện demo

## Cài đặt (Windows, Python 3.13)

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

File model **không nằm trong git**. Chép thư mục `ppe_s` (kết quả train trên Colab) vào `weights\`, sao cho có
`weights\ppe_s\weights\best.pt`. Cách train và kết quả model: [docs/huong_dan_train_ppe.md](docs/huong_dan_train_ppe.md),
[docs/ket_qua_model_ppe.md](docs/ket_qua_model_ppe.md).

## Ứng dụng web (F2)

```
copy .env.example .env                                   # 1. điền SECRET_KEY, ADMIN_PASSWORD (file .env KHÔNG đưa lên git)
.venv\Scripts\python.exe scripts\seed_demo.py --source 0 --zone ca_khung        # 2. tài khoản admin, cổng (webcam), ca, tổ đội
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000                     # 3. chạy; mở http://127.0.0.1:8000/login
```

- Thử API ở `http://127.0.0.1:8000/docs` (đăng nhập trước). Luồng hình: `/stream/gate`. Sự kiện từng lượt: WebSocket `/ws/events`.
- Đổi nguồn hình của cổng: `seed_demo.py --source <0 | URL điện thoại | file video> [--zone <tên vùng trong configs\gates.yaml>]`
  rồi gọi `POST /api/cong/khoi-dong-lai` (hoặc khởi động lại ứng dụng). Nhanh hơn: đặt `GATE_SOURCE=...` trong `.env`.
  Demo dự phòng: `--source data\raw\cong_gia_v1\du_do_01.mp4 --zone cong_gia_v1` (video tự lặp lại).
- Nhập mẫu khuôn mặt từ thư mục ảnh `<thư_mục>\<mã_công_nhân>\*.jpg`: `seed_demo.py --faces <thư_mục>` (công nhân phải có sẵn
  và đã ghi nhận đồng ý; thêm `--dong-y` nếu đã có giấy đồng ý).
- CSDL mặc định SQLite `data\safegate.db`. Dùng PostgreSQL: tạo tài khoản và CSDL (thay `MAT_KHAU`), sửa `DATABASE_URL`
  trong `.env`, rồi chạy lại bước 2:
  ```
  "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "CREATE USER safegate WITH PASSWORD 'MAT_KHAU';" -c "CREATE DATABASE safegate OWNER safegate;"
  DATABASE_URL=postgresql+psycopg://safegate:MAT_KHAU@localhost:5432/safegate
  ```
- Chạy test trên PostgreSQL (CSDL riêng cho test, bị xoá sạch mỗi test): đặt biến môi trường `SAFEGATE_TEST_DB` = URL của CSDL đó.

## Cấu hình

Mọi tham số nằm trong [configs/settings.yaml](configs/settings.yaml): đường dẫn model, `imgsz`, `conf`, `iou`,
vùng đầu/thân, các ngưỡng của thuật toán kiểm tra tại cổng, thư mục lưu ảnh. Lớp của model được tra **theo tên**
(`Person`, `Hardhat`, `Safety-Vest`). Model thiếu tên lớp nào thì chương trình báo lỗi và dừng.

## Chạy

```
# Kiểm thử tự động
.venv\Scripts\python.exe -m unittest discover -s tests -v

# Chế độ cổng. Nguồn hình (--source): file video, số webcam (0) hoặc URL điện thoại (http://.../video)
.venv\Scripts\python.exe scripts\define_zone.py --source 0 --gate cong_1                  # 1. vẽ vùng kiểm tra (tỷ lệ 0–1) -> configs\gates.yaml
.venv\Scripts\python.exe scripts\run_checkpoint.py --source 0 --gate cong_1 --rounds 3    # 2. chạy check(), ảnh + JSON -> runs\checkpoint\
# Hình bị nằm ngang (điện thoại dựng dọc): thêm --rotate 90 khi vẽ vùng; góc lưu cùng vùng, --gate tự xoay theo

# Đánh giá trên video (Giai đoạn 2). Tên file theo quy ước: du_do_01.mp4, thieu_mu_01.mp4, hai_nguoi_01.mp4,
# nguoc_sang_du_do_01.mp4... (danh sách đầy đủ trong configs\settings.yaml, mục evaluation)
.venv\Scripts\python.exe scripts\make_answers.py --videos <thu_muc_video>                 # 1. tạo dap_an.csv, kiểm tra và sửa tay
.venv\Scripts\python.exe scripts\define_zone.py --source <thu_muc_video>\du_do_01.mp4 --gate cong_video   # 2. vẽ vùng
.venv\Scripts\python.exe scripts\evaluate_videos.py --videos <thu_muc_video> --gate cong_video --imgsz 640   # 3. -> runs\eval\
.venv\Scripts\python.exe scripts\evaluate_videos.py --videos <thu_muc_video> --gate cong_video --imgsz 960

# Khuôn mặt + cổng (F1). Mô hình YuNet/SFace tải 1 lần vào weights\face\ (không commit)
.venv\Scripts\python.exe scripts\download_face_models.py
.venv\Scripts\python.exe scripts\enroll_from_images.py --camera 0 --code ME --count 5     # đăng ký mặt từ webcam (hoặc --images <thu_muc>\<ma>\*.jpg)
.venv\Scripts\python.exe scripts\run_gate.py --source 0                                   # vòng lặp cổng, cửa sổ OpenCV (q: thoát)
.venv\Scripts\python.exe scripts\run_gate.py --source data\raw\cong_gia_v1\du_do_01.mp4 --gate cong_gia_v1
.venv\Scripts\python.exe scripts\evaluate_faces.py --videos data\raw\cong_gia_v1 --answers data\annotations\cong_gia_v1.csv --gate cong_gia_v1
# Dữ liệu khuôn mặt (data\face\, data\anh_dang_ky\) là dữ liệu sinh trắc học: chỉ để trên máy, không đưa lên git

# Menu demo (báo cáo tiến độ): chọn số thay vì gõ lệnh dài. Cấu hình ở mục demo trong configs\settings.yaml
.\demo

# Công cụ khác
.venv\Scripts\python.exe scripts\extract_frames.py --source data\raw\<video>.mp4          # cắt khung để gán nhãn
.venv\Scripts\python.exe scripts\run_safety_demo.py --source data\raw\<video>.mp4         # [hướng cũ] giám sát công trường, giữ để tham khảo
```

Dùng điện thoại làm camera: [docs/huong_dan_camera_dien_thoai.md](docs/huong_dan_camera_dien_thoai.md).

## Cấu trúc

```
configs/   settings.yaml (cấu hình chung), gates.yaml (vùng kiểm tra, tạo bởi define_zone), data_ppe.yaml (dataset)
app/       ứng dụng web FastAPI: main.py, config.py (.env), db.py, models.py (các bảng), auth.py, gate_service.py (cổng chạy nền),
           events.py (WebSocket), services/ (nhan_dien, dang_ky_mat, cham_cong, luot, cong_nhan, bao_cao), routers/ (api, pages, ws, stream)
src/       config.py, checkpoint/ (kiểm tra bảo hộ: camera, evaluate, check), face/ (YuNet, SFace, phân tích mặt,
           so khớp, đăng ký), gate/ (kết hợp, máy trạng thái, một lượt, vòng lặp cổng), detection/, ppe/ (luật vùng
           đầu/thân), zone/, evaluation/, tracking/ (chỉ hướng cũ dùng), utils/
scripts/   công cụ chạy thử, vẽ vùng, cắt khung, train
tests/     kiểm thử tự động (unittest)
docs/      rà soát, hướng dẫn train, kết quả model
weights/   model đã train (không commit)
data/      video, ảnh lượt (anh_luot), ảnh mẫu mặt (anh_mau_mat), CSDL SQLite: không commit
_old/      code và file của hướng cũ (giám sát toàn công trường), không dùng nữa
```
