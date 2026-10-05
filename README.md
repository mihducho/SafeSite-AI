# SafeSite AI — Hệ thống AI đa camera giám sát an toàn lao động

Đồ án tốt nghiệp. Hệ thống hỗ trợ giám sát an toàn lao động tại công trường/nhà
máy qua nhiều camera: phát hiện vi phạm trang bị bảo hộ cá nhân (PPE) và cảnh
báo xâm nhập vùng nguy hiểm theo thời gian thực. Mỗi camera xử lý độc lập,
không cần nhận diện lại danh tính người xuyên camera.

> Đổi hướng từ đề tài cũ "LostLens — tìm trẻ lạc". Phần pipeline detect +
> tracking (YOLOv11 + BoT-SORT) được giữ lại và tái sử dụng, vì bài toán nền
> tảng (phát hiện + theo dõi người trên video) giống nhau; phần Re-ID xuyên
> camera và tìm kiếm theo thuộc tính của đề tài cũ bị loại bỏ vì không còn
> cần thiết cho an toàn lao động.

## Phạm vi

- Detection + tracking theo từng camera riêng lẻ: YOLOv11 + BoT-SORT (không Re-ID xuyên camera).
- Phát hiện vi phạm PPE: không đội nón bảo hộ / không mặc áo phản quang (mở rộng được sang kính, găng tay...).
- Cảnh báo xâm nhập vùng nguy hiểm: định nghĩa vùng cấm theo từng camera (đa giác), cảnh báo khi có người bước vào.
- Demo: 2-3 camera/video giả lập mô phỏng công trường/nhà máy, không triển khai thực tế.

## Cấu trúc thư mục

```
src/
  detection/   # YOLO — fine-tune, inference (nguoi + cac vat PPE: non, ao...)
  tracking/    # BoT-SORT, xu ly rieng tung camera (khong Re-ID xuyen camera)
  ppe/         # Kiem tra tuan thu PPE (doi chieu box nguoi va box PPE)
  zone/        # Dinh nghia + kiem tra xam nhap vung nguy hiem (polygon)
  utils/       # Video I/O, visualization, shared helpers (loc box nham lan class...)
data/
  raw/         # Video/ảnh gốc (không commit — xem .gitignore)
  processed/   # Frame đã trích/crop, dataset đã gán nhãn (PPE, person...)
  annotations/ # Nhãn bounding box
configs/       # Cấu hình tracker (botsort_*.yaml), dataset (data_ppe.yaml), vùng nguy hiểm (zones.yaml)
notebooks/     # Thử nghiệm nhanh, phân tích kết quả
scripts/       # Script chạy demo, trích frame, định nghĩa vùng, fine-tune
docs/
  related_work/ # Tổng hợp paper khảo sát
tests/
```

## Môi trường

- Python 3.13, không có GPU rời trên máy dev — fine-tune model (detection
  PPE) thực hiện trên Google Colab/Kaggle, máy local dùng để phát triển và
  test tích hợp pipeline với model nhỏ (YOLOv11n).
- Dataset PPE: khuyến nghị dùng dataset có sẵn trên Roboflow Universe (từ
  khóa "construction site safety" / "PPE detection") thay vì gán nhãn từ đầu
  — xem chi tiết comment trong `configs/data_ppe.yaml`.

## Luồng làm việc nhanh

```
# 1. Chạy thử detect + track thô (chưa có PPE/zone) trên 1 video
.venv\Scripts\python.exe scripts\run_tracking_demo.py --source data\raw\ten_video.mp4

# 2. Định nghĩa vùng nguy hiểm cho 1 camera (click chuột, không gõ tay toạ độ)
.venv\Scripts\python.exe scripts\define_zone.py --source data\raw\ten_video.mp4 --camera camera_1

# 3. Chạy demo an toàn lao động đầy đủ (PPE + vùng nguy hiểm)
.venv\Scripts\python.exe scripts\run_safety_demo.py --source data\raw\ten_video.mp4 --camera camera_1 --weights best_ppe.pt --person-cls 5 --ppe-classes 0

# (Chuẩn bị fine-tune PPE) Trích frame để gán nhãn, rồi train trên Colab
.venv\Scripts\python.exe scripts\extract_frames.py --source data\raw\ten_video.mp4
python scripts\train.py --data configs\data_ppe.yaml --weights yolo11n.pt --epochs 100
```

## Trạng thái

- [x] Khảo sát related work, chốt phạm vi đề tài (An toàn lao động — PPE + vùng nguy hiểm)
- [x] Phase 1: Detection + Tracking baseline chạy trên video mẫu (tái dùng từ đề tài cũ)
- [ ] Phase 2: Fine-tune detection PPE (nón bảo hộ, áo phản quang) trên dataset công khai + dữ liệu riêng
- [ ] Phase 3: Logic vùng nguy hiểm + tích hợp cảnh báo PPE + vùng, demo multi-camera
- [ ] Phase 4: Đánh giá, viết luận văn
