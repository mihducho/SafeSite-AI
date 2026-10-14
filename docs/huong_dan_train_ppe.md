# Hướng dẫn train model PPE cho SafeSite AI

Tài liệu này mô tả cách train model phát hiện trang bị bảo hộ (PPE) trên Google
Colab, những yêu cầu model phải đáp ứng để dùng được trong hệ thống, và những
file cần bàn giao sau khi train.

## 1. Mục tiêu

Model gốc `yolo11n.pt` / `yolo11s.pt` (huấn luyện trên COCO) chỉ biết "người",
không biết nón bảo hộ hay áo phản quang. Cần fine-tune một model YOLO để phát
hiện thêm các vật này. Model sau khi train sẽ được dùng trong
`scripts/run_safety_demo.py` để:

- phát hiện người, nón bảo hộ, áo phản quang trên từng frame;
- gán nón vào vùng đầu, áo vào vùng thân của từng người;
- báo vi phạm "KHONG NON" / "KHONG AO".

## 2. Yêu cầu về dataset

| Mức độ | Class | Ghi chú |
|---|---|---|
| Bắt buộc | Nón bảo hộ (vd `Hardhat`) | |
| Bắt buộc | Áo phản quang (vd `Safety Vest`) | |
| Rất nên có | Người (vd `Person`) | Thiếu class này thì phải chạy thêm 1 model riêng để phát hiện người → chậm gấp đôi |
| Có thì tốt | `NO-Hardhat`, `NO-Safety Vest` | Bằng chứng vi phạm trực tiếp |

- Tên class không cần đặt đúng như trên — hệ thống đọc thứ tự class từ `data.yaml`.
- Ưu tiên dataset có nhiều ảnh (vài nghìn trở lên) và có ảnh chụp từ **camera
  giám sát** (góc cao, nhìn chéo xuống), vì góc nhìn ảnh hưởng nhiều đến độ
  chính xác khi chạy demo.
- Dataset phải có tách sẵn `train` / `valid` / `test`. **Không gộp tập test vào
  train** — tập test dùng để đánh giá trong luận văn.

> **Nếu dataset không có class người:** báo lại trước khi train. Có thể dùng
> `yolo11m.pt` tự động gán box người cho toàn bộ ảnh rồi mới train, để cuối
> cùng chỉ cần 1 model.

## 3. Tham số train

| Tham số | Giá trị | Lý do |
|---|---|---|
| Model gốc | `yolo11s.pt` | Thử nghiệm cho thấy `yolo11n` nhận nhầm vật thể thành người và mất dấu nhiều; `yolo11m` quá chậm trên CPU |
| `imgsz` | `640` | Khớp kích thước ảnh khi chạy demo |
| `epochs` | `100` (dataset < 5.000 ảnh) / `50` (dataset ~9.000 ảnh) | Tránh vượt giới hạn GPU miễn phí của Colab |
| `patience` | `20` | Tự dừng sớm nếu 20 epoch liên tiếp không cải thiện |
| `batch` | `16` | Vừa với GPU T4 của Colab. Nếu báo lỗi hết bộ nhớ (`CUDA out of memory`) thì giảm xuống `8` |
| Augmentation | Mặc định của Ultralytics | |

## 4. Các bước train trên Google Colab

### Bước 1 — Tạo notebook và bật GPU

1. Vào https://colab.research.google.com → **New notebook**.
2. Menu **Runtime → Change runtime type → T4 GPU → Save**.

### Bước 2 — Kết nối Google Drive

Kết quả train được lưu thẳng lên Drive, để không bị mất khi Colab ngắt kết nối.

```python
from google.colab import drive
drive.mount('/content/drive')
```

### Bước 3 — Tải dataset từ Roboflow

1. Trên trang dataset ở Roboflow, bấm **Download Dataset** → chọn định dạng
   **YOLOv11** → chọn **Show download code**.
2. Copy đoạn code Roboflow đưa ra và chạy trong Colab. Đoạn code có dạng:

```python
!pip install -q ultralytics roboflow
from roboflow import Roboflow
rf = Roboflow(api_key="KEY_CUA_BAN")
ds = rf.workspace("ten-workspace").project("ten-project").version(1).download("yolov11")
```

> `api_key` là khóa tài khoản Roboflow của bạn — **không chia sẻ** khóa này
> và không đưa lên GitHub.

### Bước 4 — Train

```python
from ultralytics import YOLO

model = YOLO("yolo11s.pt")
model.train(
    data=f"{ds.location}/data.yaml",
    epochs=100,          # 50 nếu dataset ~9.000 ảnh
    imgsz=640,
    batch=16,
    patience=20,
    project="/content/drive/MyDrive/safesite",
    name="ppe_s",
)
```

Thời gian train tùy số ảnh, thường từ khoảng 1 đến vài tiếng. Có thể để tab
Colab chạy và làm việc khác, nhưng không đóng tab.

### Bước 5 — Nếu Colab bị ngắt giữa chừng

Chạy lại Bước 2 (kết nối Drive), cài lại thư viện, rồi train tiếp từ chỗ dừng:

```python
!pip install -q ultralytics
from ultralytics import YOLO
YOLO("/content/drive/MyDrive/safesite/ppe_s/weights/last.pt").train(resume=True)
```

### Bước 6 — Đánh giá trên tập test

Sau khi train xong, chạy đánh giá trên tập test (khác tập valid dùng trong lúc
train) để lấy số liệu cho luận văn:

```python
model = YOLO("/content/drive/MyDrive/safesite/ppe_s/weights/best.pt")
metrics = model.val(data=f"{ds.location}/data.yaml", split="test")
```

Chụp lại hoặc copy bảng kết quả in ra (mAP50, mAP50-95 theo từng class).

## 5. Tiêu chí đạt

Bảng kết quả cuối quá trình train (và ở Bước 6) có cột **mAP50** cho từng
class. Mục tiêu tham khảo:

| Class | mAP50 nên đạt |
|---|---|
| Nón bảo hộ | ≥ 0.80 |
| Áo phản quang | ≥ 0.80 |
| Người | ≥ 0.75 |

Đây là con số ước lượng để định hướng, không phải chuẩn bắt buộc. Nếu kết quả
thấp hơn nhiều, xem `results.png` và `confusion_matrix.png` để tìm nguyên nhân
(thiếu dữ liệu một class, hai class hay bị nhầm với nhau, train chưa đủ lâu...).

## 6. Bàn giao sau khi train

Tải **toàn bộ thư mục** `MyDrive/safesite/ppe_s` từ Google Drive về máy và đặt
vào `weights/ppe_s/` trong dự án (thư mục `weights/` đã nằm trong `.gitignore`,
không bị đẩy lên GitHub).

| File | Dùng để |
|---|---|
| `weights/best.pt` | Model dùng để chạy demo |
| `args.yaml` | Ghi lại tham số đã train |
| `results.csv`, `results.png` | Quá trình train qua từng epoch |
| `confusion_matrix.png` | Model hay nhầm class nào với class nào |
| `data.yaml` của dataset | Danh sách và thứ tự class (copy từ thư mục dataset trên Colab) |

Kèm theo:

- link dataset Roboflow và số version đã dùng;
- bảng kết quả đánh giá trên tập test (Bước 6).

## 7. Sau khi bàn giao

Với thông tin trong `data.yaml`, demo được chạy với đúng class id, ví dụ:

```
.venv\Scripts\python.exe scripts\run_safety_demo.py --source data\raw\ten_video.mp4 --camera camera_1 --weights weights\ppe_s\weights\best.pt --person-cls 3 --hardhat-cls 7 --vest-cls 1
```

(Với dataset `construction-site-safety-rmep1` v3: người = 3, nón = 7, áo = 1. Dùng dataset khác thì thay theo thứ tự class trong `data.yaml`.)

## Checklist

- [ ] Dataset có nón bảo hộ + áo phản quang (và nên có người)
- [ ] Đã bật GPU T4 trên Colab và kết nối Google Drive
- [ ] Train từ `yolo11s.pt`, `imgsz=640`, kết quả lưu vào `MyDrive/safesite/ppe_s`
- [ ] Đã chạy đánh giá trên tập test và lưu bảng kết quả
- [ ] Đã chép thư mục `ppe_s` về `weights/ppe_s/` + `data.yaml`
- [ ] Đã ghi lại link + version dataset
