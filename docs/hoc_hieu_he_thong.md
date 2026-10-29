# Học hiểu hệ thống SafeSite-AI, từ con số 0

Tài liệu này giải thích **toàn bộ** phần đã làm của dự án: kiến trúc, kiến thức nền, các thư viện, và từng file code
quan trọng. Ví dụ dùng **số liệu thật** của dự án (video `du_do_01`, `thieu_mu_01`... trong bộ `cong_gia_v1`).

**Cách đọc:** mở file này trong VS Code, bấm **Ctrl+Shift+V** để xem dạng đẹp. Các link dạng
[evaluate.py:64](../src/checkpoint/evaluate.py#L64) bấm vào sẽ mở đúng dòng code đang nói tới. Nên mở code song song
khi đọc.

**Nếu thời gian ít (ví dụ trước buổi demo):** đọc Bài 1, 2, 9 và 12, khoảng 45 phút. Các bài còn lại đọc sau.

## Mục lục

1. [Bức tranh tổng thể](#bài-1-bức-tranh-tổng-thể)
2. [Kiến thức nền: ảnh, khung nhận diện, YOLO](#bài-2-kiến-thức-nền)
3. [Các thư viện dùng trong dự án](#bài-3-các-thư-viện)
4. [Cấu hình: settings.yaml và config.py](#bài-4-cấu-hình)
5. [Phát hiện đối tượng: detector.py](#bài-5-phát-hiện-đối-tượng)
6. [Vùng kiểm tra: zone.py và define_zone.py](#bài-6-vùng-kiểm-tra)
7. [Lọc khung trùng: postprocess.py](#bài-7-lọc-khung-trùng)
8. [Gán mũ, áo cho người: compliance.py](#bài-8-gán-mũ-áo-cho-người)
9. [Thuật toán kiểm tra tại cổng: evaluate.py](#bài-9-thuật-toán-kiểm-tra-tại-cổng)
10. [Đọc camera: camera.py](#bài-10-đọc-camera)
11. [Một lượt kiểm tra: check.py](#bài-11-một-lượt-kiểm-tra)
12. [Theo chân một lượt kiểm tra qua toàn bộ code](#bài-12-theo-chân-một-lượt-kiểm-tra)
13. [Đánh giá trên video: thư mục evaluation](#bài-13-đánh-giá-trên-video)
14. [Kiểm thử tự động: thư mục tests](#bài-14-kiểm-thử-tự-động)
15. [Phần chưa làm và cách nối vào](#bài-15-phần-chưa-làm)
16. [Tự kiểm tra và bài tập](#bài-16-tự-kiểm-tra)
17. [Phụ lục: tra cứu file, thuật ngữ](#phụ-lục)

---

## Bài 1. Bức tranh tổng thể

### 1.1. Bài toán

Ở công trường, công nhân phải đội **mũ bảo hộ** và mặc **áo phản quang**. Hệ thống đặt ở **cổng ra vào**:

1. Công nhân quét thẻ QR ở máy kiosk, để hệ thống biết đó là ai.
2. Camera chụp liên tục trong **1.5 giây** (khoảng 18 khung hình).
3. Máy tính phân tích các khung hình, kết luận một trong bốn kết quả:
   - **ĐẠT** (`DAT`): ghi giờ vào ca.
   - **KHÔNG ĐẠT** (`KHONG_DAT`): kèm danh sách thiếu (`thieu_mu`, `thieu_ao`).
   - **KHÔNG XÁC ĐỊNH** (`KHONG_XAC_DINH`): hình không đủ rõ, mời quét lại.
   - **NHIỀU NGƯỜI** (`NHIEU_NGUOI`): có từ 2 người trong vùng, không kiểm tra.

   Ngoài ra còn kết quả **KHÔNG CÓ NGƯỜI** (`KHONG_CO_NGUOI`).

### 1.2. Hệ thống hoàn chỉnh (theo DE_TAI.md) và phần đã làm

```
   [Camera / điện thoại] --(hình liên tục)--> [ DỊCH VỤ AI (Python) ]   <-- ĐÃ LÀM
                                                       ^
                                                       | "kiểm tra người này"
  [Kiosk quét QR] ---> [ BACKEND (FastAPI) ] ----------+                  <-- CHƯA LÀM
                              |      ^
                              v      |
                       [ CSDL PostgreSQL ]   [ Web quản lý (React) ]      <-- CHƯA LÀM
```

- **Đã làm:** khối **Dịch vụ AI**, gồm đọc camera, phát hiện người, mũ, áo, và thuật toán kết luận. Cùng với đó là
  **công cụ đánh giá** trên video, **menu demo** và **158 test tự động**.
- **Chưa làm:** backend, cơ sở dữ liệu, kiosk quét QR, web quản lý (Giai đoạn 3–6).

### 1.3. Các thư mục

```
SafeSite-AI/
├── configs/        Cấu hình: settings.yaml (mọi tham số), gates.yaml (vùng kiểm tra của từng cổng)
├── src/            "THƯ VIỆN": các hàm, lớp làm việc thật (không tự chạy)
│   ├── config.py           đọc settings.yaml
│   ├── detection/          nạp model YOLO, tra số thứ tự lớp theo tên
│   ├── checkpoint/         CHẾ ĐỘ CỔNG: detector, camera, evaluate (thuật toán), check
│   ├── ppe/                gán mũ, áo cho đúng người (vùng đầu, vùng thân)
│   ├── zone/               vùng kiểm tra (đa giác), điểm chân
│   ├── utils/              lọc khung trùng, vẽ lên ảnh
│   ├── evaluation/         đánh giá trên video (Giai đoạn 2)
│   └── tracking/           theo dõi người qua nhiều khung (chỉ hướng cũ dùng)
├── scripts/        "CHƯƠNG TRÌNH": file chạy được, gọi các hàm trong src/
├── tests/          kiểm thử tự động
├── docs/           tài liệu (file này, kết quả model, kết quả đánh giá...)
├── data/           video, đáp án (video không đưa lên git)
├── weights/        file model đã train best.pt (không đưa lên git)
├── runs/           kết quả mỗi lần chạy: ảnh, JSON, CSV (không đưa lên git)
├── _old/           code hướng cũ, giữ để tham khảo
├── DE_TAI.md       đặc tả đề tài: phạm vi, thuật toán, các giai đoạn
└── demo.bat        menu demo
```

**Ý quan trọng:** `src/` là các "viên gạch", còn `scripts/` lắp các viên gạch lại thành chương trình. Ví dụ
`scripts/run_checkpoint.py` gọi `CameraReader` (đọc camera), `get_detector` (nạp model) và `check` (kiểm tra), đều nằm
trong `src/`. Tách như vậy để test được từng viên gạch, và sau này backend gọi lại đúng các hàm đó.

---

## Bài 2. Kiến thức nền

### 2.1. Ảnh trong máy tính là một bảng số

Một ảnh là một lưới điểm ảnh (pixel). Mỗi pixel có 3 số từ 0 đến 255: lượng màu **B**lue, **G**reen, **R**ed (OpenCV
dùng thứ tự **BGR**, không phải RGB). Ảnh video `du_do_01` rộng 480, cao 854, nên trong Python nó là một **mảng
numpy** có kích thước `(854, 480, 3)`: số hàng (cao), số cột (rộng), 3 màu.

**Tọa độ:** gốc `(0, 0)` ở **góc trên bên trái**. `x` tăng sang phải, `y` tăng **xuống dưới**.

### 2.2. Khung nhận diện (box)

Một vật được khoanh bằng hình chữ nhật, ghi bằng 4 số `(x1, y1, x2, y2)`: góc trên-trái và góc dưới-phải. Ví dụ thật,
khung hình đầu tiên của video `du_do_01`:

| Vật | Độ tin cậy | x1 | y1 | x2 | y2 | Ghi chú |
|---|---|---|---|---|---|---|
| Người (`Person`) | 0.88 | 131 | 55 | 363 | 828 | cao 828 − 55 = 773 px, rộng 232 px |
| Mũ bảo hộ (`Hardhat`) | 0.92 | 188 | 61 | 289 | 133 | nằm ở đỉnh đầu |
| Áo phản quang (`Safety-Vest`) | 0.92 | 166 | 193 | 332 | 484 | nằm ở thân |

### 2.3. Video và FPS

Video là chuỗi ảnh (khung hình) liên tiếp. **FPS** (frames per second) là số khung mỗi giây: camera điện thoại cho
khoảng **30 khung/giây**. Máy tính của bạn chỉ xử lý được khoảng **11 khung/giây** (khoảng 85–120 ms mỗi khung, chỉ
dùng CPU), nên **không xử lý hết** được mọi khung. Hệ thống luôn lấy **khung mới nhất** (xem Bài 10).

### 2.4. Phát hiện đối tượng và YOLO

**Phát hiện đối tượng** (object detection): đưa vào một ảnh, nhận ra danh sách các vật, mỗi vật gồm **khung + tên lớp
+ độ tin cậy** (0 đến 1). **YOLO** ("You Only Look Once") là một họ mạng nơ-ron làm việc này rất nhanh. Dự án dùng
**YOLO11s** (bản "small").

- **Train (huấn luyện):** cho mạng xem hàng nghìn ảnh đã khoanh sẵn để nó học. Bạn đã train trên Google Colab với bộ
  dữ liệu công trường **10 lớp** (Person, Hardhat, Safety-Vest, NO-Hardhat...), ra file `weights/ppe_s/weights/best.pt`.
  Độ chính xác trên tập test: mAP50 = 0.83 (xem [ket_qua_model_ppe.md](ket_qua_model_ppe.md)).
- **Suy luận (inference):** dùng model đã train để nhận diện ảnh mới. Hệ thống **chỉ suy luận**, không train.
- **Ngưỡng tin cậy `conf` = 0.35:** chỉ giữ các vật model tin chắc từ 35% trở lên.
- **NMS / `iou` = 0.7:** model hay vẽ nhiều khung chồng nhau cho cùng một vật; bước NMS (Non-Maximum Suppression) giữ
  khung tốt nhất, bỏ các khung trùng hơn 70%.
- **`imgsz` = 640:** ảnh được thu nhỏ sao cho cạnh dài bằng 640 trước khi đưa vào model (model được train ở cỡ này).
  Bản đánh giá cho thấy 960 kém hơn hẳn (Bài 13).

**Hệ thống chỉ dùng 3 lớp:** `Person`, `Hardhat`, `Safety-Vest`. Các lớp "NO-..." (không đội mũ...) không dùng để
kết luận: một người **không được gán mũ nào** thì coi là thiếu mũ.

### 2.5. Tỷ lệ 0–1 thay vì pixel

Vùng kiểm tra được lưu bằng **tỷ lệ** so với kích thước ảnh: điểm `[0.5, 1.0]` nghĩa là "giữa theo chiều ngang, ở đáy
ảnh". Lý do: cùng một vùng dùng được cho camera 480×854 hay 720×1280; khi chạy mới đổi ra pixel (Bài 6).

---

## Bài 3. Các thư viện

| Thư viện | Dùng để làm gì | Ví dụ trong dự án |
|---|---|---|
| **ultralytics** 8.4 | Nạp và chạy model YOLO | `YOLO("best.pt")`, `model.predict(frame, conf=0.35)` trong [detector.py](../src/checkpoint/detector.py) |
| **torch** (PyTorch) 2.14 | "Động cơ" tính toán mạng nơ-ron mà ultralytics dùng bên dưới | Không gọi trực tiếp |
| **opencv-python** (`cv2`) 5.0 | Đọc camera và video, xoay ảnh, vẽ khung, nén JPEG, kiểm tra điểm trong đa giác, cửa sổ click chuột | `cv2.VideoCapture`, `cv2.rotate`, `cv2.pointPolygonTest`, `cv2.imencode` |
| **numpy** 2.5 | Làm việc với mảng số (ảnh, danh sách khung) và tính toán nhanh trên cả mảng | `np.maximum`, `np.clip`, mảng `(N, 4)` các khung |
| **PyYAML** | Đọc, ghi file cấu hình `.yaml` | `yaml.safe_load` trong [config.py](../src/config.py) |
| **lap** | Thuật toán ghép cặp cho tracker (chỉ hướng cũ) | |

**Thư viện có sẵn của Python** (không cần cài):
- `pathlib` (đường dẫn file), `argparse` (đọc tham số dòng lệnh như `--source`, `--gate`).
- `threading` (chạy song song, Bài 10), `dataclasses` (khai báo lớp dữ liệu gọn).
- `csv`, `json` (ghi file kết quả), `time` (đo thời gian), `math`.
- `unittest` (kiểm thử), `subprocess` (menu demo gọi các script khác).

**Môi trường ảo `.venv`:** thư mục chứa Python riêng của dự án cùng đúng các phiên bản thư viện ghi trong
`requirements.txt`. Vì thế các lệnh đều bắt đầu bằng `.venv\Scripts\python.exe` để dùng đúng Python đó.

---

## Bài 4. Cấu hình

### 4.1. Vì sao có file cấu hình

Mọi con số có thể cần chỉnh (ngưỡng, thời gian, đường dẫn) nằm trong [configs/settings.yaml](../configs/settings.yaml),
**không viết cứng trong code**. Muốn đổi thời gian kiểm tra từ 1.5 lên 2 giây, chỉ sửa một dòng, không đụng code.

### 4.2. YAML trông thế nào

```yaml
checkpoint:
  timeout_s: 1.5               # thời gian lấy khung hình cho mỗi lần kiểm tra
  min_person_height_px: 150    # người thấp hơn 150 px -> khung không hợp lệ
  multi_person_ratio: 0.5      # >= 50% khung có 2 người -> NHIEU_NGUOI
```

Phần sau dấu `#` là chú thích. Các mục lớn: `model` (model, conf, imgsz), `ppe` (mũ, áo, vùng đầu, vùng thân),
`checkpoint` (ngưỡng thuật toán), `camera`, `evaluation`, `demo`, `paths` (đường dẫn).

### 4.3. config.py đọc file ra sao

[load_settings](../src/config.py#L35) đọc YAML thành **dict** của Python (bảng tra "khóa → giá trị"):

```python
settings = load_settings()
settings["checkpoint"]["timeout_s"]     # -> 1.5
settings["model"]["conf"]               # -> 0.35
```

Nó còn **kiểm tra đủ khóa bắt buộc** (thiếu thì báo lỗi ngay khi khởi động, thay vì chạy được nửa chừng mới hỏng), và
đổi các đường dẫn tương đối thành tuyệt đối ([project_path](../src/config.py#L29)) để chạy ở thư mục nào cũng đúng.

---

## Bài 5. Phát hiện đối tượng

File: [src/checkpoint/detector.py](../src/checkpoint/detector.py) và [src/detection/detect.py](../src/detection/detect.py).

### 5.1. Tra lớp theo tên

Model có 10 lớp, đánh số 0–9 (ví dụ `Person` = 3, `Hardhat` = 7). Code **không ghi cứng số 3, số 7** mà tra theo tên
bằng [find_class_ids](../src/detection/detect.py#L19). Nếu sau này đổi sang model khác có thứ tự lớp khác, code vẫn
đúng; thiếu tên nào thì báo lỗi kèm danh sách lớp của model.

### 5.2. YoloDetector: bọc model lại

```python
class YoloDetector:
    def __init__(self, settings, model=None):
        self.model = load_model(...)                  # nạp best.pt
        self.classes = [3, 7, 1]                      # Person, Hardhat, Safety-Vest (tra theo tên)
        self.predict_kw = {"conf": 0.35, "iou": 0.7, "imgsz": 640}   # lấy từ settings

    def __call__(self, frame):                        # gọi detector(frame) như gọi hàm
        boxes = self.model.predict(frame, classes=self.classes, **self.predict_kw)[0].boxes
        return Detections(xyxy=..., cls=..., conf=...)  # mảng khung, mảng lớp, mảng độ tin cậy
```
(rút gọn từ [detector.py:23](../src/checkpoint/detector.py#L23))

- **`Detections`** ([detector.py:17](../src/checkpoint/detector.py#L17)) là một "hộp" chứa 3 mảng: `xyxy` (N khung × 4
  số), `cls` (lớp của từng khung), `conf` (độ tin cậy).
- **Vì sao bọc lại?** Thuật toán phía sau chỉ cần "đưa ảnh vào, nhận `Detections` ra". Khi test, ta thay bằng
  **bộ phát hiện giả** trả về khung soạn sẵn, nên test chạy được mà không cần model hay video (Bài 14).
- **`warmup()`:** lần chạy model đầu tiên chậm khoảng 1.5 giây do khởi tạo, nên lúc nạp model chạy thử một lần trên ảnh
  đen. Nếu không, lượt kiểm tra đầu tiên chỉ kịp xử lý một khung.
- **[get_detector](../src/checkpoint/detector.py#L49):** nạp model **một lần** rồi dùng lại (bộ nhớ đệm), vì nạp mất vài
  giây.

---

## Bài 6. Vùng kiểm tra

File: [src/zone/zone.py](../src/zone/zone.py), [scripts/define_zone.py](../scripts/define_zone.py), vùng lưu ở
[configs/gates.yaml](../configs/gates.yaml).

### 6.1. Vì sao cần vùng

Camera có thể thấy cả người đi ngang phía sau. Hệ thống chỉ xét người **đứng trong vùng kiểm tra**, tức phần sàn trước
camera nơi công nhân đứng.

### 6.2. Lưu vùng

```yaml
cong_gia_v1:
  zone:                 # các đỉnh đa giác, tỷ lệ 0-1
  - [0.0, 0.0014]
  - [0.9951, 0.0014]
  - [0.9951, 1.0]
  - [0.0, 1.0]
  rotate: 0             # góc xoay hình của camera cổng này
```

[zone_to_pixels](../src/zone/zone.py#L97) đổi ra pixel lúc chạy: với ảnh 480×854, điểm `[0.9951, 1.0]` thành
`[478, 854]` (vì 0.9951 × 480 ≈ 478, 1.0 × 854 = 854).

### 6.3. Điểm chân và kiểm tra trong vùng

- [person_feet_point](../src/zone/zone.py#L116): lấy **điểm giữa cạnh dưới** khung người, tức là chỗ bàn chân.
  Ví dụ `du_do_01`: `((131 + 363) / 2, 828)` = **(247, 828)**.
- [point_in_zone](../src/zone/zone.py#L111): dùng `cv2.pointPolygonTest` để hỏi "điểm này có nằm trong đa giác
  không". Nằm trong thì người đó được tính là "trong vùng".

Vì sao dùng chân chứ không dùng tâm khung? Vì vị trí đứng trên sàn quyết định người đó có ở cổng hay không. Người ở
xa phía sau có thể có khung chồng lên vùng, nhưng chân thì ở ngoài.

### 6.4. Vẽ vùng bằng chuột (define_zone.py)

1. [grab_frame](../scripts/define_zone.py#L37) lấy một khung hình từ video hoặc camera.
2. `cv2.imshow` hiện ảnh. `cv2.setMouseCallback` đăng ký hàm [on_click](../scripts/define_zone.py#L80) được gọi mỗi
   lần click, để lưu tọa độ điểm.
3. Bấm `s`: [clicks_to_ratio](../src/zone/zone.py#L29) đổi pixel sang tỷ lệ, rồi
   [save_gate_zone](../src/zone/zone.py#L60) ghi vào `gates.yaml`.

**Xoay hình** (`rotate`): điện thoại dựng dọc mà app phát hình ngang thì người trong hình nằm ngang. Đặt `rotate: 90`
để hệ thống xoay lại cho đứng thẳng. Góc xoay lưu cùng vùng, vì vùng được vẽ trên hình đã xoay.

---

## Bài 7. Lọc khung trùng

File: [src/utils/postprocess.py](../src/utils/postprocess.py), hàm [suppress_contained](../src/utils/postprocess.py#L10).

### 7.1. Vấn đề

Đôi khi model vẽ **2 khung cho 1 người**: một khung cả người và một khung nhỏ (nửa thân trên) nằm gần trọn bên trong.
Nếu không lọc, hệ thống tưởng có 2 người và báo `NHIEU_NGUOI` sai.

### 7.2. Cách lọc

Với mỗi cặp khung, tính **phần trăm diện tích khung nhỏ nằm trong khung lớn**. Nếu ≥ **80%** (`contain_thresh`) thì bỏ
khung nhỏ.

```
 tỷ lệ nằm trong = diện tích phần giao nhau / diện tích khung nhỏ
```

### 7.3. Trường hợp khung gộp

Khi 2 người **đứng sát vai**, model có thể vẽ thêm một khung lớn bao cả hai. Nếu chỉ lọc như trên thì 2 khung từng
người bị bỏ (vì nằm trong khung lớn), còn lại khung lớn: hệ thống tưởng chỉ có 1 người. Code xử lý thêm: nếu một khung
lớn chứa **≥ 2 khung đứng cạnh nhau** (chồng nhau theo chiều ngang ≤ 50%) thì khung lớn là **khung gộp**: bỏ khung gộp,
giữ từng người ([_group_boxes](../src/utils/postprocess.py#L47)).

### 7.4. Hạn chế đã biết

Khi 2 người đứng **trước–sau**, khung người phía sau nằm 84–99% trong khung người phía trước nên bị bỏ như khung trùng.
Đây là lý do 3 video "hai người đứng trước–sau" bị sai (xem [ket_qua_danh_gia_cong_v1.md](ket_qua_danh_gia_cong_v1.md)).

---

## Bài 8. Gán mũ, áo cho người

File: [src/ppe/compliance.py](../src/ppe/compliance.py), hàm [assign_ppe](../src/ppe/compliance.py#L60).

### 8.1. Vùng đầu và vùng thân

Model trả về khung mũ, khung áo **riêng** với khung người. Phải biết mũ đó có **trên đầu người này** không. Code chia
khung người theo chiều cao (cấu hình ở mục `ppe.items` của settings):

- **Vùng đầu:** từ −10% đến 35% chiều cao, tính từ đỉnh khung. Lấy âm 10% vì mũ hay nhô lên khỏi đỉnh khung người.
- **Vùng thân:** từ 15% đến 70% chiều cao.

Ví dụ `du_do_01`: người cao 773 px, đỉnh ở y = 55:
- vùng đầu: y từ 55 − 0.1 × 773 ≈ **−23** đến 55 + 0.35 × 773 ≈ **325**.
- vùng thân: y từ **171** đến **596**.

### 8.2. Mũ có nằm trong vùng không

```
 tỷ lệ = diện tích (khung mũ ∩ vùng đầu) / diện tích khung mũ        (hàm _inside_ratio)
 tỷ lệ >= 0.5 (min_inside)  ->  người này CÓ mũ
```

Chia cho diện tích **khung mũ**, không chia cho diện tích người: mũ chỉ chiếm vài phần trăm khung người, nếu chia cho
diện tích người thì không bao giờ đạt ngưỡng.

**Ví dụ thật:**

| Video | Vật | Vị trí (pixel) | Tỷ lệ trong vùng | Kết luận khung |
|---|---|---|---|---|
| `du_do_01` | Mũ | y 61–133 | 1.00 trong vùng đầu | có mũ |
| `du_do_01` | Áo | y 193–484 | 1.00 trong vùng thân | có áo |
| `thieu_mu_01` | Áo | y 196–472 | 1.00 | có áo |
| `thieu_mu_01` | "Mũ" | x 425–480, y 628–677 | **0.00** | **không** có mũ |

Ở `thieu_mu_01`, model **có** thấy một mũ bảo hộ, nhưng đó là chiếc mũ đặt trong cảnh ở góc dưới bên phải, không nằm
trên đầu ai. Luật vùng đầu giúp hệ thống không bị lừa.

### 8.3. Mỗi mũ chỉ thuộc về một người

Khi có nhiều người, mỗi mũ được gán cho người có tỷ lệ cao nhất (`argmax`), để 2 người đứng sát nhau không "dùng chung"
một mũ.

### 8.4. Người cúi

Người cúi gập thì đầu không còn ở phía trên. Nếu khung người có **cao / rộng < 1** (khung bè ngang), code bỏ vùng đầu,
vùng thân và xét **cả khung**.

---

## Bài 9. Thuật toán kiểm tra tại cổng

File: [src/checkpoint/evaluate.py](../src/checkpoint/evaluate.py). Đây là **trái tim** của hệ thống. Thuật toán chạy 2
bước:

### 9.1. Bước 1: xét từng khung (classify_frame)

Hàm [classify_frame](../src/checkpoint/evaluate.py#L64) nhận kết quả model của **một** khung và trả về loại khung:

```
 khung hình
   │
   ├─ lọc khung trùng (Bài 7)
   ├─ giữ người có điểm chân trong vùng (Bài 6)          -> dòng 83
   │
   ├─ 0 người        -> "trong"
   ├─ >= 2 người     -> "nhieu_nguoi"
   └─ đúng 1 người:
        ├─ cao < 150 px                    -> "khong_hop_le" (qua_nho)   -> dòng 92
        ├─ đỉnh khung chạm mép trên ảnh    -> "khong_hop_le" (cat_dau)   -> dòng 94
        └─ còn lại -> "hop_le" + ghi có mũ? có áo? (Bài 8)               -> dòng 99
```

Vì sao loại khung "đầu bị cắt"? Đầu nằm ngoài ảnh thì không thể biết có đội mũ hay không, nên không dùng khung đó để
kết luận.

### 9.2. Bước 2: tổng hợp và bỏ phiếu (aggregate)

Hàm [aggregate](../src/checkpoint/evaluate.py#L103) nhận khoảng 18 kết quả của bước 1, kiểm tra **theo thứ tự**:

1. **≥ 50%** số khung là `nhieu_nguoi` → **NHIEU_NGUOI** ([dòng 121](../src/checkpoint/evaluate.py#L121)).
2. Có **ít hơn 3** khung hợp lệ ([dòng 124](../src/checkpoint/evaluate.py#L124)): quá nửa là `trong` thì ra
   **KHONG_CO_NGUOI**, ngược lại ra **KHONG_XAC_DINH**.
3. Với từng món, tính **tỷ lệ có mặt** = số khung hợp lệ thấy món đó / số khung hợp lệ:
   - ≥ **0.6** → **có**.
   - ≤ **0.2** → **thiếu**.
   - Ở giữa → **không chắc**.
4. Có món không chắc → **KHONG_XAC_DINH**. Có món thiếu → **KHONG_DAT** kèm danh sách. Còn lại → **DAT**.

**Ví dụ thật:**

| Video | Kết quả từng khung (18 khung) | Tính toán | Kết luận |
|---|---|---|---|
| `du_do_01` | 18 hợp lệ, mũ 18/18, áo 18/18 | mũ 1.0 ≥ 0.6, áo 1.0 ≥ 0.6 | **DAT** |
| `thieu_mu_01` | 18 hợp lệ, mũ 0/18, áo 18/18 | mũ 0.0 ≤ 0.2 | **KHONG_DAT** thiếu mũ |
| `non_la_03` | 18 hợp lệ, "mũ" 4/18 | 4/18 = 0.22, nằm giữa 0.2 và 0.6 | **KHONG_XAC_DINH** |
| `hai_nguoi_canhnhau_01` | 18/18 khung `nhieu_nguoi` | 100% ≥ 50% | **NHIEU_NGUOI** |
| `hai_nguoi_dungsau_03` | 6 khung `nhieu_nguoi`, 12 hợp lệ | 6/18 = 33% < 50%, xét tiếp người phía trước | KHONG_DAT (sai) |

**Vì sao bỏ phiếu nhiều khung?** Model có thể bỏ sót mũ ở 1–2 khung (người quay đầu, mờ). Xét 18 khung thì vài khung
sai không làm đổi kết luận. **Vì sao có "không chắc"?** Tại cổng, quét lại chỉ mất vài giây; kết luận sai thì hoặc chặn
nhầm người đủ đồ, hoặc cho người thiếu đồ đi qua. Không chắc thì mời quét lại, không đoán.

### 9.3. FrameEvaluator, ảnh chụp và evaluate_frames

- [FrameEvaluator](../src/checkpoint/evaluate.py#L197) gói bước 1 và bước 2: `add(frame)` gọi model và
  `classify_frame` cho một khung, `finish()` gọi `aggregate` và đóng gói kết quả.
- `SnapshotPicker` chọn **một ảnh đại diện** để lưu: ưu tiên khung hợp lệ có người lớn nhất, rồi vẽ vùng và khung người
  (xanh = đủ, đỏ + chữ = thiếu).
- [evaluate_frames](../src/checkpoint/evaluate.py#L248) nhận **danh sách khung có sẵn**, dùng để chạy trên video và để
  test.

**Kết quả trả về** là một dict: `ket_qua`, `thieu`, `ty_le_co_mat`, `dem_khung` (đếm khung theo loại), `ly_do`,
`thoi_gian_ms`, `anh_jpeg`...

---

## Bài 10. Đọc camera

File: [src/checkpoint/camera.py](../src/checkpoint/camera.py), lớp [CameraReader](../src/checkpoint/camera.py#L89).

### 10.1. Vấn đề độ trễ

Camera đưa ra 30 khung/giây, máy chỉ xử lý được khoảng 11 khung/giây. Nếu đọc lần lượt, các khung chưa xử lý xếp hàng
trong bộ đệm. Sau vài giây, hệ thống phân tích hình **của mấy giây trước**, khi công nhân còn chưa bước vào.

### 10.2. Giải pháp: một luồng riêng, chỉ giữ khung mới nhất

**Luồng** (thread) là một "công nhân phụ" chạy song song với chương trình chính. `CameraReader` tạo một luồng
([dòng 119](../src/checkpoint/camera.py#L119)) chỉ làm một việc: đọc camera liên tục, và mỗi khung mới **ghi đè** khung
cũ ([dòng 163](../src/checkpoint/camera.py#L163)). Chương trình chính cần hình thì lấy khung mới nhất, không bao giờ
phải chờ hàng đợi.

```
 Luồng camera:  đọc khung 1 -> lưu | đọc khung 2 -> ghi đè | đọc khung 3 -> ghi đè | ...
 Luồng chính:          lấy khung mới nhất -> xử lý 85 ms -> lấy khung mới nhất -> ...
```

- [wait_new(after_id, timeout)](../src/checkpoint/camera.py#L150): "chờ đến khi có khung mới hơn khung số `after_id`".
  Mỗi khung có một số thứ tự tăng dần (`_frame_id`). Hai luồng phối hợp qua `threading.Condition`: luồng camera báo
  "có khung mới", luồng chính đang chờ thì thức dậy.
- **Mất kết nối** (Wi-Fi chập chờn): luồng camera tự đóng và mở lại sau 2 giây (`_reconnect`).
- **Nguồn là file video:** phát đúng tốc độ thật (30 khung/giây), không đọc nhanh hết, để mô phỏng camera thật. Hết
  video thì phát lại từ đầu.
- **Xoay hình:** khung được xoay ngay khi đọc ([dòng 185](../src/checkpoint/camera.py#L185)), nên mọi bước sau đều thấy
  hình đứng thẳng.
- Nguồn hình nhận 3 kiểu ([parse_source](../src/checkpoint/camera.py#L62)): số (`0` = webcam), URL (`http://...` =
  điện thoại), còn lại là file video.

**Cú pháp `with`:**
```python
with CameraReader("http://192.168.1.10:4747/video", cam_cfg) as cam:   # mở camera, chạy luồng đọc
    ...                                                                 # dùng cam
# ra khỏi khối with: tự dừng luồng, đóng camera (kể cả khi có lỗi)
```

---

## Bài 11. Một lượt kiểm tra

File: [src/checkpoint/check.py](../src/checkpoint/check.py), hàm [check](../src/checkpoint/check.py#L18). Hàm này ngắn
nhưng quan trọng:

```python
def check(reader, zone, ...):
    evaluator = FrameEvaluator(zone, ...)       # chuẩn bị (Bài 9)
    deadline = bây_giờ + 1.5 giây
    last_id = reader.latest_id                  # chỉ xét khung MỚI HƠN lúc bấm kiểm tra
    while còn thời gian:
        last_id, frame = reader.wait_new(last_id, thời_gian_còn_lại)
        evaluator.add(frame)                    # xử lý NGAY khung vừa lấy (khoảng 85 ms)
    return evaluator.finish()                   # bỏ phiếu -> DAT / KHONG_DAT / ...
```

Mỗi vòng xử lý xong một khung (khoảng 85 ms) thì lấy khung **mới nhất** lúc đó. Trong 1.5 giây xử lý được khoảng 18
khung. Không nhận được khung nào thì báo `CameraError`, nghĩa là lỗi thiết bị, không phải kết luận về người.

---

## Bài 12. Theo chân một lượt kiểm tra

Khi bạn chạy (hoặc chọn số 2 trong menu demo):
```
.venv\Scripts\python.exe scripts\run_checkpoint.py --source data\raw\cong_gia_v1\du_do_01.mp4 --gate cong_gia_v1 --rounds 1
```
Thứ tự code được gọi:

| # | Ở đâu | Làm gì |
|---|---|---|
| 1 | [run_checkpoint.py main](../scripts/run_checkpoint.py#L40) | `argparse` đọc các tham số `--source`, `--gate`, `--rounds` |
| 2 | [load_settings](../src/config.py#L35) | Đọc `settings.yaml` thành dict |
| 3 | [load_gate](../src/zone/zone.py#L44), [choose_rotate](../src/zone/zone.py#L73) | Lấy vùng `cong_gia_v1` (tỷ lệ 0–1) và góc xoay (0) |
| 4 | [get_detector](../src/checkpoint/detector.py#L49) | Nạp `best.pt`, tra lớp theo tên, chạy warmup (khoảng 1.5 s) |
| 5 | [CameraReader.start](../src/checkpoint/camera.py#L114) | Mở video, bật luồng đọc khung (Bài 10) |
| 6 | [check](../src/checkpoint/check.py#L18) | Vòng lặp 1.5 giây (Bài 11). **Với mỗi khung:** |
| 6a | [FrameEvaluator.add](../src/checkpoint/evaluate.py#L222) | Đổi vùng ra pixel ([zone_to_pixels](../src/zone/zone.py#L97)) |
| 6b | [YoloDetector.\_\_call\_\_](../src/checkpoint/detector.py#L34) | Model YOLO tìm người, mũ, áo → `Detections` |
| 6c | [classify_frame](../src/checkpoint/evaluate.py#L64) | Lọc khung trùng → người trong vùng → kích thước, đầu bị cắt → [assign_ppe](../src/ppe/compliance.py#L60) |
| 6d | `SnapshotPicker.offer` | Ghi nhớ khung tốt nhất để chụp ảnh |
| 7 | [FrameEvaluator.finish](../src/checkpoint/evaluate.py#L236) | [aggregate](../src/checkpoint/evaluate.py#L103) bỏ phiếu → `DAT`; vẽ và nén ảnh JPEG |
| 8 | run_checkpoint.py | Ghi ảnh `.jpg` và kết quả `.json` vào `runs\checkpoint\`, in kết quả ra màn hình |
| 9 | `reader.stop()` | Dừng luồng camera |

Màn hình in ra (số khung tùy tốc độ máy lúc chạy, khoảng 14–18):
```
[Luot 1] DAT
   ty_le_co_mat={'hardhat': 1.0, 'vest': 1.0} | dem_khung={... 'hop_le': 14}
```

**Nếu hiểu được bảng này, bạn hiểu được hệ thống.** Các bài 5–11 là chi tiết của từng dòng trong bảng.

---

## Bài 13. Đánh giá trên video

Thư mục [src/evaluation/](../src/evaluation/), script [evaluate_videos.py](../scripts/evaluate_videos.py) và
[make_answers.py](../scripts/make_answers.py).

### 13.1. Quy trình

```
 video đặt tên theo quy ước (du_do_01.mp4, thieu_mu_02.mp4...)
   │ make_answers.py: đoán đáp án từ tên file -> data/annotations/cong_gia_v1.csv (bạn kiểm tra tay)
   ▼
 evaluate_videos.py: với từng video
   ├─ lấy khoảng 18 khung trong 1.5 giây đầu, MÔ PHỎNG đúng tốc độ máy (video.py)
   ├─ evaluate_frames (Bài 9) -> kết quả
   └─ so với đáp án -> đúng / sai
   ▼
 metrics.py tính chỉ số -> report.py ghi tom_tat.md, ket_qua.csv, ảnh lượt sai
```

### 13.2. Mô phỏng tốc độ (video.py)

Máy xử lý 11.7 khung/giây, tức mỗi khung khoảng 85 ms. Trong 1.5 giây, các thời điểm bắt đầu xử lý là 0, 0.085,
0.171... giây, được **18 thời điểm** ([sample_times](../src/evaluation/video.py#L16)). Video 29.8 FPS nên thời điểm `t`
ứng với khung số `t × 29.8`, ra các khung 0, 2, 5, 7, 10... đúng như danh sách lấy mẫu thật của video `du_do_01`.

### 13.3. Các chỉ số (metrics.py)

- **Tỷ lệ đúng:** số lượt kết quả trùng đáp án / tổng số lượt. Kết quả: 38/43 = 88.4%.
- **Ma trận nhầm lẫn:** bảng "đáp án × kết quả". Đường chéo là đúng.
- **Vi phạm là "dương tính"** (chỉ xét các video có đáp án ĐẠT hoặc KHÔNG ĐẠT):
  - **Precision** = báo vi phạm đúng / tổng số lần báo vi phạm = 20/20 = **100%**. Không chặn nhầm ai.
  - **Recall** = vi phạm bị phát hiện / tổng số vi phạm thật = 20/22 = **90.9%**.
  - **Bỏ lọt** = vi phạm nhưng hệ thống ra ĐẠT. Đây là lỗi nguy hiểm nhất; có 1 lượt (nón lá).

Xem kết quả và phân tích đầy đủ ở [ket_qua_danh_gia_cong_v1.md](ket_qua_danh_gia_cong_v1.md).

### 13.4. Menu demo

[scripts/demo.py](../scripts/demo.py) chỉ hiện menu rồi gọi lại các script trên bằng `subprocess`. Thông số lấy từ mục
`demo` trong `settings.yaml`. `demo.bat` là file chạy nhanh trên Windows.

---

## Bài 14. Kiểm thử tự động

Thư mục [tests/](../tests/). Chạy toàn bộ:
```
.venv\Scripts\python.exe -m unittest discover -s tests -v
```
Mỗi `test_...` là một hàm kiểm tra **một tình huống**. Ví dụ trong [test_checkpoint.py](../tests/test_checkpoint.py):

```python
def test_khong_dat_thieu_ao(self):
    r = run([NO_VEST] * 5)                       # 5 khung: có người + mũ, KHÔNG có áo
    self.assertEqual((r["ket_qua"], r["thieu"]), (KHONG_DAT, ["thieu_ao"]))   # phải ra thiếu áo
```

**Dữ liệu giả** ([tests/fakes.py](../tests/fakes.py)):
- `FakeDetector`: thay model, trả về khung soạn sẵn (người ở `[500, 100, 700, 650]`, mũ ở `[560, 80, 640, 150]`...).
  Nhờ vậy test thuật toán **không cần model, không cần video**, chạy cả trăm test trong 5 giây.
- `FakeCapture`: thay camera, sinh khung hình đánh số. Dùng để test luồng đọc camera: chỉ giữ khung mới nhất, tự kết
  nối lại, phát video đúng tốc độ...

**Vì sao cần test?** Mỗi lần sửa code, chạy lại toàn bộ test để chắc không làm hỏng chỗ khác. Ví dụ khi đổi ngưỡng
nhiều người từ "quá nửa" sang 25% rồi 50%, test cho biết ngay trường hợp nào đổi kết quả.

---

## Bài 15. Phần chưa làm

Theo DE_TAI.md, các giai đoạn tiếp theo sẽ **gọi lại** đúng các hàm đã có:

- **Backend** (FastAPI, Python): một máy chủ web. Khi kiosk gửi "công nhân X quét thẻ ở cổng 1", backend gọi
  `check(reader, zone, ...)` (Bài 11) rồi lưu kết quả và ảnh vào cơ sở dữ liệu.
- **Cơ sở dữ liệu** (PostgreSQL, dùng SQLAlchemy): các bảng công nhân, cổng (gồm vùng kiểm tra và góc xoay, đang tạm
  lưu ở `gates.yaml`), lượt kiểm tra, chấm công.
- **Kiosk** (React): màn hình ở cổng, quét QR bằng camera (thư viện `html5-qrcode`), hiện kết quả ĐẠT / KHÔNG ĐẠT.
- **Web quản lý** (React): quản lý công nhân, xem lịch sử, xác nhận các lượt bị chặn, xuất bảng chấm công.

---

## Bài 16. Tự kiểm tra

**Câu hỏi** (đáp án ngắn ngay dưới mỗi câu):

1. Vì sao hệ thống xét nhiều khung chứ không xét 1 khung?
   *Một khung có thể nhận sai; bỏ phiếu theo khoảng 18 khung thì ổn định hơn.*
2. Vì sao chiếc mũ đặt trên bàn không làm người không đội mũ được tính là "có mũ"?
   *Mũ chỉ được tính khi ≥ 50% diện tích khung mũ nằm trong vùng đầu của người (Bài 8).*
3. Vì sao có luồng đọc camera riêng?
   *Để luôn lấy khung mới nhất, tránh xử lý hình cũ trong hàng đợi (Bài 10).*
4. `KHONG_XAC_DINH` xảy ra khi nào?
   *Khi có ít hơn 3 khung hợp lệ mà không phải do vắng người, hoặc khi tỷ lệ có mặt của một món nằm giữa 0.2 và 0.6.*
5. Vì sao lưu vùng bằng tỷ lệ 0–1?
   *Để dùng được cho mọi độ phân giải camera.*
6. Vì sao chọn imgsz 640 chứ không phải 960?
   *Ở 960, model tách một người thành hai khung, nên báo nhiều người sai; lại chậm gấp đôi.*
7. File nào chứa thuật toán bỏ phiếu? Hàm nào?
   *`src/checkpoint/evaluate.py`, hàm `aggregate`.*

**Bài tập** (làm trên máy, không làm hỏng gì):

1. Chạy toàn bộ test (lệnh ở Bài 14), xem có bao nhiêu test, tất cả có OK không.
2. **Thử ngưỡng tin cậy.** Mở [settings.yaml](../configs/settings.yaml), đổi `conf: 0.35` thành `conf: 0.9`, lưu
   lại, rồi chạy menu demo số 2 (video `du_do_01`). Kết quả đổi từ `DAT` thành **`KHONG_CO_NGUOI`**: model chỉ tin
   khoảng 88% đây là người, thấp hơn ngưỡng 0.9, nên người bị bỏ qua. (Với `0.6` thì không có gì thay đổi.) Xong
   nhớ **đổi lại `0.35`**.
3. Mở file `.json` mới nhất trong `runs\checkpoint\`, tìm phần `chi_tiet_khung`. Mỗi dòng là một khung: đọc lớp, độ
   tin cậy, tọa độ, loại khung.
4. **Làm một test chạy sai.** Trong [test_checkpoint.py](../tests/test_checkpoint.py), tìm hàm
   `test_khong_dat_thieu_ao`, sửa `["thieu_ao"]` thành `["thieu_mu"]`, rồi chạy lại toàn bộ test. Bạn sẽ thấy
   `FAILED (failures=1)` kèm thông báo kết quả thật khác kết quả mong đợi thế nào. Đó là cách test bắt lỗi. Xong nhớ
   **sửa lại** như cũ.

---

## Phụ lục

### A. Tra cứu nhanh: file nào làm gì

| File | Vai trò |
|---|---|
| [configs/settings.yaml](../configs/settings.yaml) | Mọi tham số |
| [configs/gates.yaml](../configs/gates.yaml) | Vùng kiểm tra và góc xoay của từng cổng |
| [src/config.py](../src/config.py) | Đọc settings.yaml |
| [src/detection/detect.py](../src/detection/detect.py) | Nạp model, tra lớp theo tên |
| [src/checkpoint/detector.py](../src/checkpoint/detector.py) | Bọc model: ảnh vào, `Detections` ra |
| [src/checkpoint/camera.py](../src/checkpoint/camera.py) | Luồng đọc camera / video, xoay hình |
| [src/checkpoint/evaluate.py](../src/checkpoint/evaluate.py) | **Thuật toán**: xét từng khung, bỏ phiếu |
| [src/checkpoint/check.py](../src/checkpoint/check.py) | Một lượt kiểm tra 1.5 giây trên camera |
| [src/ppe/compliance.py](../src/ppe/compliance.py) | Gán mũ, áo theo vùng đầu, vùng thân |
| [src/utils/postprocess.py](../src/utils/postprocess.py) | Lọc khung trùng, khung gộp |
| [src/utils/visualize.py](../src/utils/visualize.py) | Vẽ vùng, khung người lên ảnh |
| [src/zone/zone.py](../src/zone/zone.py) | Vùng kiểm tra, điểm chân, đọc/ghi gates.yaml |
| [src/evaluation/](../src/evaluation/) | Đáp án, lấy mẫu video, chỉ số, báo cáo (Giai đoạn 2) |
| [scripts/run_checkpoint.py](../scripts/run_checkpoint.py) | Chạy thử kiểm tra trên camera / video |
| [scripts/define_zone.py](../scripts/define_zone.py) | Vẽ vùng bằng chuột |
| [scripts/make_answers.py](../scripts/make_answers.py) | Tạo file đáp án từ tên video |
| [scripts/evaluate_videos.py](../scripts/evaluate_videos.py) | Đánh giá cả bộ video |
| [scripts/demo.py](../scripts/demo.py) | Menu demo |
| [scripts/train.py](../scripts/train.py) | Train model (đã chạy trên Colab) |
| `scripts/run_safety_demo.py`, `src/tracking/` | Hướng cũ (giám sát toàn công trường), giữ để tham khảo |

### B. Thuật ngữ

| Thuật ngữ | Nghĩa |
|---|---|
| Khung hình (frame) | Một ảnh trong video |
| Khung nhận diện (box) | Hình chữ nhật khoanh một vật, `(x1, y1, x2, y2)` |
| Độ tin cậy (confidence) | Model chắc chắn bao nhiêu (0–1) |
| Lớp (class) | Loại vật: Person, Hardhat, Safety-Vest... |
| Suy luận (inference) | Dùng model đã train để nhận diện |
| FPS | Số khung mỗi giây |
| Luồng (thread) | Phần chương trình chạy song song |
| Vùng kiểm tra (zone) | Đa giác trên sàn nơi công nhân đứng |
| Điểm chân | Điểm giữa cạnh dưới khung người |
| Tỷ lệ có mặt | Số khung hợp lệ thấy món đồ / số khung hợp lệ |
| Precision / Recall | Báo vi phạm đúng bao nhiêu / phát hiện được bao nhiêu vi phạm |
| mAP50 | Chỉ số độ chính xác chuẩn của model phát hiện đối tượng |
