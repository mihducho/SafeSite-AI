# SafeSite-AI

Đồ án tốt nghiệp: **hệ thống quản lý và chấm công công nhân tại công trường, tích hợp kiểm tra trang bị
bảo hộ lao động bằng thị giác máy tính**.

Công nhân quét thẻ QR ở kiosk tại cổng. Camera kiểm tra người đứng trong vùng kiểm tra có đội mũ bảo hộ
và mặc áo phản quang không (YOLO11s). Đạt thì ghi giờ vào ca. Mô tả đầy đủ, phạm vi và các quyết định
đã chốt nằm ở [DE_TAI.md](DE_TAI.md).

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
- [ ] Giai đoạn 2–6: script đánh giá, backend, kiosk, web quản lý (xem DE_TAI.md mục 10)

## Cài đặt (Windows, Python 3.13)

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

File model **không nằm trong git**. Chép thư mục `ppe_s` (kết quả train trên Colab) vào `weights\`, sao cho có
`weights\ppe_s\weights\best.pt`. Cách train và kết quả model: [docs/huong_dan_train_ppe.md](docs/huong_dan_train_ppe.md),
[docs/ket_qua_model_ppe.md](docs/ket_qua_model_ppe.md).

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

# Công cụ khác
.venv\Scripts\python.exe scripts\extract_frames.py --source data\raw\<video>.mp4          # cắt khung để gán nhãn
.venv\Scripts\python.exe scripts\run_safety_demo.py --source data\raw\<video>.mp4         # [hướng cũ] giám sát công trường, giữ để tham khảo
```

Dùng điện thoại làm camera: [docs/huong_dan_camera_dien_thoai.md](docs/huong_dan_camera_dien_thoai.md).

## Cấu trúc

```
configs/   settings.yaml (cấu hình chung), gates.yaml (vùng kiểm tra, tạo bởi define_zone), data_ppe.yaml (dataset)
src/       config.py, checkpoint/ (chế độ cổng: camera, evaluate, check), detection/, ppe/ (luật vùng đầu/thân),
           zone/, tracking/ (chỉ hướng cũ dùng), utils/
scripts/   công cụ chạy thử, vẽ vùng, cắt khung, train
tests/     kiểm thử tự động (unittest)
docs/      rà soát, hướng dẫn train, kết quả model
weights/   model đã train (không commit)
_old/      code và file của hướng cũ (giám sát toàn công trường), không dùng nữa
```
