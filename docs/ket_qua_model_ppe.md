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

## Thử trên video công trường (2026-10-16): lệch miền dữ liệu với áo cam/đỏ

Trên 2 video công trường tự tìm (test2: 4K cận cảnh, áo đỏ; test3: 1280×720,
công nhân ở xa, áo cam), model nhận nón tốt nhưng gần như **không nhận ra áo
phản quang**, thậm chí dự đoán `NO-Safety-Vest` cho người đang mặc áo, và nhầm
áo cam thành `Safety-Cone`. Logic gán PPE vẫn đúng: áo nào được phát hiện đều
được gán đúng vào vùng thân.

Tổng số phát hiện trên 3 frame mỗi video (conf 0.35):

| Video | imgsz | Person | Hardhat | Safety-Vest | NO-Safety-Vest |
|---|---|---|---|---|---|
| test3 | 640 | 13 | 17 | 0 | 7 |
| test3 | 960 | 18 | 21 | 8 | 9 |
| test3 | 1280 | 21 | 25 | 4 | 8 |
| test2 | 640 | 9 | 4 | 0 | 4 |
| test2 | 960 | 3 | 5 | 1 | 1 |

Nhận định: áo phản quang trong dataset chủ yếu màu vàng-xanh, chụp gần → model
không tổng quát sang áo cam/đỏ (phổ biến ở công trường Việt Nam) và người ở xa.
Tăng `imgsz` lên 960 cải thiện một phần (đã đặt làm mặc định trong
`run_safety_demo.py`), nhưng cách sửa gốc là bổ sung dữ liệu áo cam/đỏ, người ở
xa, góc camera giám sát rồi train tiếp — frame dùng để train phải lấy từ video
khác với video dùng để đánh giá.

## Sửa lỗi pipeline và đo lại trên video công trường (2026-10-16)

Ba lỗi trong pipeline (không phải do model) làm báo nhầm thiếu PPE:

1. **Tracker theo dõi cả box PPE.** `model.track()` ghép box giữa các frame không
   phân biệt class → mất ~65% box nón, 42% box áo (test5, 40 frame đầu: nón 335
   → 116), có ID bị đổi class. Sửa: tracker chỉ nhận box người
   (`PersonTracker`), box PPE lấy thẳng từ detect từng frame.
2. **2 box Person cho 1 người** (người cúi/bị che): nón gán cho box này, áo cho
   box kia → cả 2 "người" thiếu PPE. NMS của YOLO không loại vì IoU ~0.5. Sửa:
   bỏ box người nằm ≥ 80% trong box người lớn hơn (`suppress_contained`).
3. **Người cúi gập/ngồi xổm:** đầu không nằm ở 35% phía trên box. Sửa: box có
   cao/rộng < 1 thì nón/áo chỉ cần nằm trong box người.

Kết quả trên test6 (1 người mặc đủ nón + áo, 438 frame 4K, tỉ lệ lượt người bị
đánh dấu vi phạm):

| Pipeline | Vi phạm (bất kỳ) | Thiếu nón | Thiếu áo | Số ID |
|---|---|---|---|---|
| Ban đầu | 28.4% | 26.5% | 8.4% | 4 |
| + bỏ box người trùng | 23.8% | 23.1% | 4.2% | 3 |
| + xử lý tư thế cúi | **8.1%** | 7.3% | 4.2% | 3 |

Phần còn lại là các đoạn ngắn (dài nhất 12 frame ≈ 0.24 s) → làm mượt theo
thời gian sẽ loại được.

test5 (camera di chuyển, ~15 công nhân, 593 frame) sau khi sửa: 36.9% lượt bị
đánh dấu (thiếu nón 31.0%, thiếu áo 13.5%); tracker cấp 281 ID, track trung vị
chỉ 7 frame. Cách đếm hiện tại (ID bị đánh dấu ≥ 1 frame) báo **231 người**; mô
phỏng làm mượt (≥ 70% của 30 frame) còn **6 người** — cả 6 đều đang đội nón
(báo nhầm). Trong 36 frame thiếu nón của 6 người này: 53% model có thấy nón
nhưng conf 0.10–0.34 (dưới ngưỡng 0.35), 39% không thấy nón kể cả conf 0.10
(nón trắng, quay lưng, ngồi), 8% bị che khuất nên không gán được.

Việc tiếp theo: làm mượt theo thời gian + đếm theo sự kiện; ngưỡng conf riêng
(thấp hơn) cho nón/áo — cần kiểm tra trên video người không đội nón để tránh bỏ
lọt vi phạm thật; bổ sung dữ liệu nón trắng, người quay lưng/ở xa, áo cam/đỏ.

## Hạn chế

- Tập test nhỏ (278 ảnh) và cùng nguồn với dữ liệu train (chủ yếu frame cắt từ
  video YouTube, chụp gần), ít ảnh góc camera giám sát. Kết quả trên camera thật
  có thể thấp hơn → cần đánh giá thêm trên video tự quay (Phase 4).
- Chạy thử trên video camera gia đình (CPU, ~7 FPS): báo đúng vi phạm cho người
  không có PPE, không còn nhận nhầm vật thể thành người như yolo11n COCO, nhưng
  vẫn bỏ sót người ngồi bị che một phần và vẫn cấp nhiều ID cho cùng một người.
