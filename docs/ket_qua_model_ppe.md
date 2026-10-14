# Kết quả model PPE (ppe_s)

## Thông tin train

| Mục | Giá trị |
|---|---|
| Dataset | Roboflow `007-kd2zw/construction-site-safety-rmep1` version 3 (CC BY 4.0) — https://universe.roboflow.com/007-kd2zw/construction-site-safety-rmep1/dataset/3 |
| Số class | 10: Mask, Safety-Vest, NO-Safety-Vest, Person, machinery, Safety-Cone, vehicle, Hardhat, NO-Mask, NO-Hardhat |
| Model gốc | `yolo11s.pt` (pretrained COCO) |
| Tham số | `epochs=100`, `imgsz=640`, `batch=16`, `patience=20`, augmentation mặc định |
| Phần cứng | Google Colab, Tesla T4 |
| Thời gian train | ~2,5 giờ (100 epoch, không dừng sớm) |
| Thư viện | Ultralytics 8.4.177, torch 2.11.0 |
| Weights | `weights/ppe_s/weights/best.pt` (không commit; epoch tốt nhất: 99) |

Class id dùng khi chạy demo: người = 3, nón = 7, áo = 1
(`--person-cls 3 --hardhat-cls 7 --vest-cls 1`).

## Kết quả trên tập test (278 ảnh, 4.046 đối tượng)

| Class | Ảnh | Đối tượng | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|---|---|
| **all** | 278 | 4046 | 0.913 | 0.752 | **0.833** | **0.586** |
| Mask | 124 | 206 | 0.940 | 0.806 | 0.891 | 0.647 |
| **Safety-Vest** | 143 | 343 | 0.930 | 0.771 | **0.852** | 0.622 |
| NO-Safety-Vest | 195 | 451 | 0.939 | 0.781 | 0.842 | 0.613 |
| **Person** | 268 | 1065 | 0.933 | 0.833 | **0.910** | 0.707 |
| machinery | 212 | 468 | 0.949 | 0.920 | 0.963 | 0.839 |
| Safety-Cone | 58 | 412 | 0.860 | 0.556 | 0.696 | 0.351 |
| vehicle | 67 | 139 | 0.927 | 0.748 | 0.867 | 0.632 |
| **Hardhat** | 144 | 345 | 0.918 | 0.742 | **0.810** | 0.527 |
| NO-Mask | 158 | 334 | 0.854 | 0.666 | 0.724 | 0.415 |
| NO-Hardhat | 151 | 283 | 0.876 | 0.696 | 0.772 | 0.509 |

Tốc độ trên T4: 2.1 ms tiền xử lý + 10.6 ms suy luận + 4.5 ms hậu xử lý / ảnh.

## So sánh với tập valid (epoch 99)

| | mAP50 valid | mAP50 test |
|---|---|---|
| all | 0.827 | 0.833 |
| Person | 0.900 | 0.910 |
| Safety-Vest | 0.804 | 0.852 |
| Hardhat | 0.792 | 0.810 |
| NO-Safety-Vest | 0.853 | 0.842 |
| NO-Hardhat | 0.804 | 0.772 |

Điểm test xấp xỉ valid → model không bị khớp quá mức với tập valid.

## Nhận xét

- Ba class hệ thống dùng (Person, Hardhat, Safety-Vest) đều đạt mục tiêu
  tham khảo (Person ≥ 0.75, Hardhat/Safety-Vest ≥ 0.80 mAP50).
- Precision cao (~0.92) nhưng recall thấp hơn (~0.74–0.77 với nón/áo): model
  ít báo nhầm nhưng bỏ sót khoảng 1/4 số nón/áo. Trong hệ thống, việc bỏ sót nón
  dẫn đến cảnh báo nhầm "KHONG NON" → cần làm mượt theo thời gian và cân nhắc
  ngưỡng tin cậy riêng (thấp hơn) cho nón/áo.
- Confusion matrix (tập valid): ~7% trường hợp NO-Hardhat bị nhận thành Hardhat
  → bỏ lọt vi phạm thật.

## Hạn chế

- Tập test nhỏ (278 ảnh) và cùng nguồn với dữ liệu train (chủ yếu frame cắt từ
  video YouTube, chụp gần), ít ảnh góc camera giám sát. Kết quả trên camera thật
  có thể thấp hơn → cần đánh giá thêm trên video tự quay (Phase 4).
- Chạy thử trên video camera gia đình (CPU, ~7 FPS): báo đúng vi phạm cho người
  không có PPE, không còn nhận nhầm vật thể thành người như yolo11n COCO, nhưng
  vẫn bỏ sót người ngồi bị che một phần và vẫn cấp nhiều ID cho cùng một người.
