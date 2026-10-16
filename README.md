# SafeSite-AI

Đồ án tốt nghiệp: **hệ thống quản lý và chấm công công nhân tại công trường, tích hợp kiểm tra trang bị
bảo hộ lao động bằng thị giác máy tính**.

Công nhân quét thẻ QR ở kiosk tại cổng. Camera kiểm tra người đứng trong vùng kiểm tra có đội mũ bảo hộ
và mặc áo phản quang không (YOLO11s). Đạt thì ghi giờ vào ca. Mô tả đầy đủ, phạm vi và các quyết định
đã chốt nằm ở [DE_TAI.md](DE_TAI.md).

## Trạng thái

- [x] Giai đoạn 0: rà soát code cũ, xem [docs/RA_SOAT.md](docs/RA_SOAT.md)
- [x] Giai đoạn 1a: dọn code hướng cũ vào `_old/`, file cấu hình chung, tra lớp theo tên, ghim thư viện
- [ ] Giai đoạn 1b: dịch vụ AI chế độ cổng (`evaluate_frames`, `check`, đọc camera)
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

# Chế độ cổng: chưa có, làm ở Giai đoạn 1b.

# Công cụ có sẵn
.venv\Scripts\python.exe scripts\define_zone.py --source data\raw\<video>.mp4 --camera cong_1   # vẽ vùng bằng chuột
.venv\Scripts\python.exe scripts\extract_frames.py --source data\raw\<video>.mp4                 # cắt khung để gán nhãn
.venv\Scripts\python.exe scripts\run_safety_demo.py --source data\raw\<video>.mp4               # [hướng cũ] giám sát công trường, giữ để tham khảo
```

## Cấu trúc

```
configs/   settings.yaml (cấu hình chung), botsort_tracking.yaml, data_ppe.yaml (dataset)
src/       config.py, detection/, ppe/ (luật vùng đầu/thân), zone/, tracking/, utils/
scripts/   công cụ chạy thử, vẽ vùng, cắt khung, train
tests/     kiểm thử tự động (unittest)
docs/      rà soát, hướng dẫn train, kết quả model
weights/   model đã train (không commit)
_old/      code và file của hướng cũ (giám sát toàn công trường), không dùng nữa
```
