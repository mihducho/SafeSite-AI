# RÀ SOÁT DỰ ÁN CŨ VÀ ĐỐI CHIẾU VỚI DE_TAI.md

- Ngày rà soát: 2026-10-16. Commit đang rà: `d1e9342` (nhánh `main`). `DE_TAI.md` chưa được commit (`git status`: `?? DE_TAI.md`).
- Chỉ đọc, không sửa file nào. Các lệnh chạy thử chỉ đọc video và in kết quả ra màn hình, không ghi vào dự án.
- Ký hiệu bằng chứng: `file:dòng`, hoặc "lệnh:" kèm kết quả.

---

## A. TỔNG QUAN

### Cây thư mục (bỏ `.git/`, `.venv/`, `__pycache__/`)

```
SafeSite-AI/
├── DE_TAI.md, README.md, requirements.txt, .gitignore
├── yolo11n.pt, yolo11s.pt, yolo11m.pt     # model gốc COCO (không commit)
├── configs/
│   ├── botsort_tracking.yaml, botsort_tracking_reid.yaml
│   ├── data_ppe.yaml                      # mô tả dataset PPE 10 lớp
│   └── zones.yaml                         # vùng cấm: camera_1, camera_5, camera_6, camera_7
├── src/
│   ├── detection/detect.py                # load_model(), detect()
│   ├── tracking/tracker.py                # PersonTracker, track()
│   ├── ppe/compliance.py                  # luật gán PPE theo vùng đầu/thân
│   ├── zone/zone.py                       # đọc vùng, kiểm tra điểm trong đa giác
│   └── utils/postprocess.py, visualize.py
├── scripts/
│   ├── run_safety_demo.py                 # script chính hiện tại (PPE + vùng cấm)
│   ├── define_zone.py                     # vẽ vùng bằng chuột
│   ├── run_tracking_demo.py, sanity_check.py, extract_frames.py, train.py
├── tests/  test_compliance.py, test_zone.py, test_tracker.py, test_postprocess.py
├── weights/ppe_s/                         # kết quả train trên Colab (không commit)
│   ├── weights/best.pt, last.pt
│   └── args.yaml, data.yaml, results.csv, *.png
├── docs/   huong_dan_train_ppe.md, ket_qua_model_ppe.md, related_work/ (trống)
├── data/   raw/ (test01, test2, test3, test5, test6 .mp4), processed/ (trống), annotations/ (trống)
├── notebooks/ (trống)
├── runs/   detect/, safety/ (15 video kết quả)  # không commit
└── _archive_lostlens/                     # dữ liệu đề tài cũ LostLens (không commit)
```

### Ngôn ngữ và thư viện (lệnh: in phiên bản trong `.venv`)

| Thành phần | Phiên bản |
|---|---|
| Python | 3.13.7 (Windows) |
| ultralytics | 8.4.152 |
| torch | 2.14.0, **không có CUDA** (`torch.cuda.is_available()` = False) |
| opencv-python | 5.0.0.93 |
| numpy | 2.5.3 |
| lap | 0.5.13 |
| PyYAML | 6.0.3 |
| fastapi, sqlalchemy, psycopg2, qrcode, uvicorn | **không cài** |

`requirements.txt:2-6` chỉ ghi giới hạn dưới (`>=`), không ghim phiên bản. Kiểm thử: `python -m unittest discover -s tests`, kết quả 24 test, **OK**.

### Cách chạy hiện tại (`README.md:51-73`)

```
# Vẽ vùng cấm cho 1 camera
.venv\Scripts\python.exe scripts\define_zone.py --source data\raw\<video>.mp4 --camera camera_1
# Chạy kiểm tra PPE + vùng cấm, xuất video có vẽ kết quả
.venv\Scripts\python.exe scripts\run_safety_demo.py --source data\raw\<video>.mp4 --camera camera_1 --weights weights\ppe_s\weights\best.pt --person-cls 3 --hardhat-cls 7 --vest-cls 1
```

---

## B. PHẦN AI

**1. File model**
- Mặc định là `yolo11n.pt` (COCO 80 lớp) khi không truyền `--weights`: `src/detection/detect.py:7`, `scripts/run_safety_demo.py:51,87`.
- Model PPE chỉ được dùng khi truyền tay `--weights weights\ppe_s\weights\best.pt` (`scripts/run_safety_demo.py:9`).

**2. Danh sách lớp thật của best.pt**
- Lệnh `YOLO('weights/ppe_s/weights/best.pt').names`:
  `{0: 'Mask', 1: 'Safety-Vest', 2: 'NO-Safety-Vest', 3: 'Person', 4: 'machinery', 5: 'Safety-Cone', 6: 'vehicle', 7: 'Hardhat', 8: 'NO-Mask', 9: 'NO-Hardhat'}`. Khớp với `DE_TAI.md:29-30`.
- Tham số lúc train: `weights/ppe_s/args.yaml:3` (`model: yolo11s.pt`), `:5` (`epochs: 100`), `:9` (`imgsz: 640`).

**3. Tham số suy luận** (`scripts/run_safety_demo.py`)

| Tham số | Giá trị | Bằng chứng |
|---|---|---|
| imgsz | **960** (khác với lúc train là 640) | `:55` |
| conf | 0.35, dùng chung cho mọi lớp | `:52` |
| iou (NMS) | không đặt, nên dùng mặc định Ultralytics 0.7 | `.venv/.../ultralytics/cfg/default.yaml:56` |
| classes | `[person_cls] + [hardhat_cls, vest_cls]` | `:88` |

**4. Tracking**
- **Có**, dùng BoT-SORT qua lớp `PersonTracker`, chỉ theo dõi box người: `src/tracking/tracker.py:14-44`, `scripts/run_safety_demo.py:91,110`.
- Cấu hình ở `configs/botsort_tracking.yaml`, ReID tắt. `PersonTracker` từ chối cấu hình bật ReID (`tracker.py:26-28`).
- `run_tracking_demo.py` vẫn dùng `model.track()` cũ (`tracker.py:45-67`, `run_tracking_demo.py:61`).

**5. Lớp NO-\***
- **Không dùng trong logic.** Bộ lọc `classes` chỉ gồm người, nón và áo (`run_safety_demo.py:88`).
- Chỉ được nhắc trong docstring (`src/ppe/compliance.py:10-11`).

**6. Logic quyết định vi phạm hiện tại** (xét từng khung hình riêng lẻ)
1. Detect, rồi lấy box có `cls == person_cls` (`run_safety_demo.py:107`).
2. Bỏ box người nằm ≥ 80% diện tích bên trong một box người lớn hơn (`src/utils/postprocess.py:10-35`, gọi ở `run_safety_demo.py:108-109`).
3. Gán mỗi box nón hoặc áo cho **một** người: người có vùng chứa phần lớn nhất của box PPE, và chỉ tính khi tỉ lệ ≥ 0.5 (`compliance.py:54-90`, `min_inside=0.5` ở `:59`).
   - Vùng đầu là `(-0.1, 0.35)` chiều cao box người, vùng thân là `(0.15, 0.7)` (`compliance.py:19-20`).
   - Nếu box người có chiều cao < chiều rộng (người cúi hoặc ngồi) thì dùng cả box (`compliance.py:25-26, 75-84`).
4. Người thiếu bất kỳ món nào đang bật kiểm tra thì bị coi là vi phạm **trong khung đó** (`run_safety_demo.py:117-120`).
5. Bộ đếm in ra là số track ID bị đánh dấu **ít nhất 1 khung** (`:94, 119-120, 146`). **Không có** bước gộp nhiều khung hay bỏ phiếu theo thời gian.
6. Danh sách đồ bảo hộ bật hoặc tắt qua cờ `--hardhat-cls`, `--vest-cls` (`run_safety_demo.py:38-44, 59-60`).

**7. Nguồn hình**
- Truyền thẳng `source` cho `model.predict(..., stream=True)` (`detect.py:25`, `run_safety_demo.py:90`).
- **File video: đã chạy được** trên `data/raw/test*.mp4`.
- **Webcam và RTSP/HTTP: CHƯA XÁC MINH.**
  - Ultralytics có bộ đọc luồng chạy trong luồng riêng và chỉ giữ khung mới nhất khi `stream_buffer: False` (mặc định ở `default.yaml:66`; `ultralytics/data/loaders.py:153, 222`). Nhưng chưa chạy thử với camera điện thoại.
  - `run_safety_demo.py:79-84` dùng `cv2.VideoCapture(source)` để lấy FPS và `Path(source).stem` để đặt tên file ra. Với webcam (`"0"`) hoặc URL thì hai chỗ này chạy ra sao là CHƯA XÁC MINH.

**8. Tốc độ** (lệnh: đo trên 80 khung của `test3.mp4` 1280×720, gồm detect, tracking và gán PPE, không ghi video, CPU)

| imgsz | Tốc độ |
|---|---|
| 640 | **6.6 FPS** |
| 960 | **2.9 FPS** |

Lần chạy đầy đủ trước đó trên video 4K `test5.mp4` (593 khung, có ghi video) mất 4 phút 33 giây, khoảng **2.2 FPS**.

---

## C. VÙNG CẤM

- **Vẽ bằng gì:** cửa sổ OpenCV (`cv2.imshow`) trên **một khung hình** lấy từ video (`scripts/define_zone.py:49-90`).
  - Click chuột trái để thêm điểm, ít nhất 3 điểm. Phím `s` lưu, `r` vẽ lại, `q` thoát.
  - Khung lớn hơn 1280×720 được thu nhỏ khi hiển thị, rồi tọa độ được quy đổi về kích thước gốc (`define_zone.py:56-58, 85`).
- **Lưu ở đâu:** `configs/zones.yaml`, dạng `{tên_camera: [[x, y], ...]}` (`define_zone.py:30-38`). Hiện có `camera_1, camera_5, camera_6, camera_7`.
- **Định dạng tọa độ:** **pixel tuyệt đối** của khung hình gốc, được làm tròn (`define_zone.py:35`), **không phải tỷ lệ 0–1**. Ví dụ `camera_5` có điểm `[2098, 1342]` trên video 3842×2160.
- **Điểm dùng để kiểm tra:** **điểm chân**, tức trung điểm cạnh dưới của box người (`src/zone/zone.py:29-34`). Kiểm tra bằng `cv2.pointPolygonTest` (`zone.py:24-26`), gọi ở `run_safety_demo.py:121`.

---

## D. BACKEND, CƠ SỞ DỮ LIỆU, GIAO DIỆN

**Chưa có.**
- Không có framework web, cơ sở dữ liệu, API hay trang giao diện nào. Thư viện tương ứng chưa cài (mục A).
- Không có `package.json`, `frontend/`, `Dockerfile`, `docker-compose.yml` (lệnh `ls`: "No such file or directory").
- Giao diện duy nhất là cửa sổ OpenCV: `--show` ở `run_safety_demo.py:135-138`, và cửa sổ vẽ vùng.
- `requirements.txt:8` chỉ có dòng chú thích "Sẽ bổ sung ... fastapi + uvicorn".

---

## E. LƯU TRỮ VÀ CẢNH BÁO

| Loại | Lưu ở đâu, định dạng | Bằng chứng |
|---|---|---|
| Video kết quả (cả video, có vẽ khung) | `runs/safety/<tên>_<camera>_<thời gian>.mp4`, codec mp4v | `run_safety_demo.py:31, 84, 101, 133` |
| Kết quả tracking demo | `runs/detect/track-N/` (Ultralytics tự lưu) | `run_tracking_demo.py:61` (`save=True`) |
| Ảnh trích từ video | `data/processed/frames_<tên>/*.jpg` | `extract_frames.py:27, 41-42` |
| Ảnh chụp lúc vi phạm | **Không có** | |
| Log hoặc kết quả vi phạm | Chỉ in ra terminal, không ghi file | `run_safety_demo.py:144-149` |
| Thông báo | **Không có** | |

`runs/`, `weights/`, `*.pt`, `data/raw/*` đều bị git bỏ qua (`.gitignore:9, 13, 16, 17`).

---

## F. BẢNG ĐỐI CHIẾU VỚI DE_TAI.md

### Mục 3: Hiện trạng dự án (DE_TAI.md mô tả đúng chưa?)

| Mục trong DE_TAI.md | Hiện trạng trong code | Trạng thái | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| YOLO11s, Colab, dataset rmep1 v3, imgsz 640, epochs 100, file best.pt (`:27-28`) | Đúng. Đường dẫn file là `weights/ppe_s/weights/best.pt` | KHỚP | `args.yaml:3,5,9`; `weights/ppe_s/data.yaml` (roboflow workspace 007-kd2zw, version 3) | Ghi rõ đường dẫn file trong DE_TAI.md |
| 10 lớp, đúng thứ tự (`:29-30`) | Đúng | KHỚP | lệnh `model.names` (mục B.2) | — |
| Code phát hiện người có đội mũ, mặc áo hay không (`:31`) | Có, theo luật vùng đầu và thân | KHỚP | `compliance.py:54-90` | — |
| Chức năng vẽ vùng cấm đa giác (`:32`) | Có, bằng cửa sổ OpenCV | KHỚP | `define_zone.py`, `zone.py` | — |
| Hai script `ppe_monitor.py` (head_region, torso_region, has_item, tracking) và `clean_dataset.py` (`:33`, `:41`) | **Không tồn tại.** Không có trong dự án, cũng không tìm thấy trên `D:\02_Projects_Code` (độ sâu 6) và `E:\` (độ sâu 3). Không có hàm `head_region`, `torso_region`, `has_item`. Chức năng tương đương nằm ở `HEAD_REGION`, `TORSO_REGION`, `_region_boxes`, `assign_ppe` | LỆCH | lệnh `Get-ChildItem -Include ppe_monitor.py, clean_dataset.py` không có kết quả; `compliance.py:19-20, 36-40, 54-90` | Xem câu hỏi J1 |

### Mục 4: Quyết định đã chốt

| Mục trong DE_TAI.md | Hiện trạng trong code | Trạng thái | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| Giữ YOLO11s best.pt, không đổi model (`:37`) | best.pt có, nhưng **mặc định** code tải `yolo11n.pt` COCO | LỆCH | `detect.py:7`; `run_safety_demo.py:51, 87` | Đưa đường dẫn best.pt vào file cấu hình, làm mặc định |
| Không dùng lớp NO-\*; chỉ dùng Person, Hardhat, Safety-Vest (`:38`) | Đúng, chỉ lọc 3 lớp này | KHỚP | `run_safety_demo.py:88` | — |
| Tìm lớp theo TÊN trong `model.names`, không ghi cứng số thứ tự (`:39`) | **Truyền số thứ tự** qua tham số dòng lệnh; tài liệu ghi cứng 3/7/1; mặc định `person_cls=0` | LỆCH | `run_safety_demo.py:9, 58-60`; `compliance.py:32` (`cls_id: int`); `README.md:65` | Tra chỉ số lớp theo tên từ `model.names` |
| Luật vùng cơ thể: nón trong vùng đầu (~30% trên), áo trong vùng thân (`:40`) | Có. Vùng đầu (-0.1, 0.35), vùng thân (0.15, 0.7), ngưỡng 0.5. Có thêm 2 quy tắc: người cúi thì dùng cả box; bỏ box người trùng | KHỚP | `compliance.py:19-26, 59, 75-89`; `postprocess.py:10-35` | Đưa các ngưỡng ra file cấu hình (DE_TAI mục 11.6). Về con số 0.35 so với ~30%, xem J2 |
| Tái sử dụng `head_region`, `torso_region`, `has_item` trong `ppe_monitor.py` (`:41`) | Không có các hàm và file này | LỆCH | như mục 3 | Xem J1 |
| Vẽ vùng cấm cũ, tái sử dụng thành "vùng kiểm tra" (`:42`) | Chưa có khái niệm vùng kiểm tra. Đã có sẵn công cụ vẽ và hàm kiểm tra điểm trong đa giác | CHƯA CÓ | `define_zone.py`; `zone.py:24-34` | Tái sử dụng `point_in_zone`, `person_feet_point`; tọa độ xem J4 |
| Nhận diện công nhân bằng mã QR (`:43`) | Không có | CHƯA CÓ | `qrcode` chưa cài (mục A) | Giai đoạn 3–4 |
| Nội dung QR là UUID (`:44`) | Không có | CHƯA CÓ | — | Giai đoạn 3 |
| Ảnh lưu thành file, cơ sở dữ liệu lưu đường dẫn; không lưu video liên tục (`:45`) | Ngược lại: ghi **cả video** có vẽ khung, không lưu ảnh, không có cơ sở dữ liệu | LỆCH | `run_safety_demo.py:84, 101, 133` | Chế độ cổng chỉ trả về 1 ảnh JPEG mỗi lượt |
| Chạy tất cả trên 1 laptop (`:46`) | Mọi thứ chạy cục bộ trên CPU | KHỚP | `torch.cuda.is_available()` = False; FPS ở mục B.8 | Lưu ý tốc độ CPU (H6) |
| Điện thoại làm camera IP RTSP/HTTP (`:46-47`) | Ultralytics hỗ trợ trên lý thuyết, **chưa chạy thử** | KHÔNG XÁC ĐỊNH ĐƯỢC | `detect.py:25`; `loaders.py:56-222` | Chạy thử ở Giai đoạn 1 |
| Webcam laptop để quét QR (`:47`) | Không có | CHƯA CÓ | — | Giai đoạn 4 (html5-qrcode) |

### Mục 5 (rút gọn): Kết quả trả về của dịch vụ AI

| Mục trong DE_TAI.md | Hiện trạng trong code | Trạng thái | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| `check(timeout=1.5)` trả về DAT / KHONG_DAT (thiếu gì) / KHONG_XAC_DINH / NHIEU_NGUOI / KHONG_CO_NGUOI kèm ảnh (`:54-60`, `:171`) | Không có. Hiện chỉ xét từng khung và đếm theo track ID, không có cửa sổ thời gian | CHƯA CÓ | `run_safety_demo.py:96-133` | Viết module `checkpoint` (Giai đoạn 1), dùng lại `assign_ppe`, `suppress_contained`, `point_in_zone` |

### Mục 8: Công nghệ

| Mục trong DE_TAI.md | Hiện trạng trong code | Trạng thái | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| Dịch vụ AI: Python, Ultralytics YOLO11s, OpenCV | Đúng các công nghệ này, nhưng mới là script, chưa là "dịch vụ" | KHỚP | mục A | — |
| Backend: FastAPI, SQLAlchemy, PostgreSQL, WebSocket | Không có, chưa cài | CHƯA CÓ | mục A, D | — |
| Frontend: React (Vite) | Không có | CHƯA CÓ | không có `package.json` | — |
| Quét QR: html5-qrcode | Không có | CHƯA CÓ | — | — |
| Sinh QR, in thẻ: `qrcode`, PDF | Không có | CHƯA CÓ | `qrcode` chưa cài | — |
| Lưu ảnh: thư mục cấu hình được | Chỉ có thư mục video ghi cứng `runs/safety` | LỆCH | `run_safety_demo.py:31` | Đưa vào file cấu hình |
| Docker Compose | Không có | CHƯA CÓ | không có `docker-compose.yml` | — |
| "Dự án đã có công nghệ khác thì báo lại" (`:124`) | Không có công nghệ backend, cơ sở dữ liệu hay frontend nào khác. Chỉ có thêm: BoT-SORT (tracking), YAML (cấu hình), `unittest` (kiểm thử) | KHỚP | `tracker.py`; `configs/*.yaml`; `tests/` | Không xung đột |

### Mục 8: Nguyên tắc kiến trúc

| Mục trong DE_TAI.md | Hiện trạng trong code | Trạng thái | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| Backend là trung tâm | Chưa có backend | CHƯA CÓ | mục D | — |
| AI chỉ "nhìn và trả lời", không ghi cơ sở dữ liệu | Script không ghi cơ sở dữ liệu, nhưng tự ghi video ra đĩa | LỆCH | `run_safety_demo.py:101, 133` | Dịch vụ AI chỉ trả kết quả và JPEG |
| Backend gửi vùng kiểm tra và danh sách đồ bảo hộ trong mỗi yêu cầu | Vùng đọc từ `zones.yaml` theo tên camera; danh sách PPE lấy từ tham số dòng lệnh | LỆCH | `run_safety_demo.py:38-44, 69-70` | Hàm kiểm tra nhận đa giác và danh sách PPE làm tham số (tái dùng `build_rules`) |
| Đọc camera bằng luồng riêng, chỉ giữ khung mới nhất | Ultralytics có cơ chế này cho nguồn luồng, chưa kiểm chứng trên dự án | KHÔNG XÁC ĐỊNH ĐƯỢC | `default.yaml:66`; `loaders.py:153, 222` | Kiểm chứng ở Giai đoạn 1 |
| Cung cấp luồng hình có vẽ khung để xem trực tiếp | Chỉ có cửa sổ OpenCV và file mp4 | CHƯA CÓ | `run_safety_demo.py:135-138` | Tái dùng `visualize.py` |
| Kiosk dùng khóa riêng của cổng | Không có | CHƯA CÓ | — | — |
| AI không phản hồi thì kiosk báo gián đoạn | Không có | CHƯA CÓ | — | — |

### Mục 9: Cơ sở dữ liệu

| Bảng trong DE_TAI.md | Hiện trạng trong code | Trạng thái | Bằng chứng | Đề xuất |
|---|---|---|---|---|
| `users` | Không có cơ sở dữ liệu | CHƯA CÓ | mục D | — |
| `teams` | Không có | CHƯA CÓ | mục D | — |
| `workers` (qr_token UUID) | Không có | CHƯA CÓ | mục D | — |
| `gates` (vùng kiểm tra JSON, cấu hình PPE) | Không có bảng. Dữ liệu vùng hiện ở `configs/zones.yaml` (pixel) | CHƯA CÓ | `zones.yaml` | Định dạng xem J4 |
| `ppe_checks` | Không có | CHƯA CÓ | mục D | — |
| `shifts` | Không có | CHƯA CÓ | mục D | — |
| `shift_assignments` | Không có | CHƯA CÓ | mục D | — |
| `attendance` | Không có | CHƯA CÓ | mục D | — |
| `settings` | Không có | CHƯA CÓ | mục D | — |

---

## G. KHẢ NĂNG TÁI SỬ DỤNG

| File hoặc thư mục | Xếp loại | Lý do |
|---|---|---|
| `src/ppe/compliance.py` | SỬA LẠI | Giữ thuật toán `assign_ppe`, `missing_ppe` (có test). Đổi `cls_id` số thành tra theo tên lớp; đưa ngưỡng ra file cấu hình |
| `src/utils/postprocess.py` | SỬA LẠI | Giữ `suppress_contained`. Hàm `make_class_overlap_filter` (lọc người nhầm xe máy) chỉ phục vụ demo hướng cũ |
| `src/zone/zone.py` | GIỮ NGUYÊN | `point_in_zone`, `person_feet_point` dùng được cho vùng kiểm tra |
| `src/tracking/tracker.py` | GIỮ NGUYÊN | `PersonTracker` dùng được nếu cần gom các khung của cùng một người (J3). Hàm `track()` chỉ demo cũ dùng |
| `src/detection/detect.py` | SỬA LẠI | Đổi model mặc định từ `yolo11n.pt` sang best.pt qua file cấu hình |
| `src/utils/visualize.py` | SỬA LẠI | Hàm vẽ khung và chữ dùng lại được cho luồng hình xem trực tiếp; bỏ nhãn "XAM NHAP" của hướng cũ |
| `scripts/define_zone.py` | GIỮ NGUYÊN | Vẽ vùng kiểm tra trên video tự quay cho tới khi web có chức năng vẽ |
| `scripts/run_safety_demo.py` | SỬA LẠI | Làm khung cho script chạy thử chế độ cổng (Giai đoạn 1); logic đếm theo track ID và ghi video là của hướng cũ |
| `scripts/extract_frames.py` | GIỮ NGUYÊN | Cắt khung từ video tự quay |
| `scripts/train.py` | GIỮ NGUYÊN | Chưa train lại (DE_TAI:37), giữ để dùng sau. Lưu ý: mặc định `--weights yolo11n.pt` (`train.py:19`) |
| `scripts/run_tracking_demo.py` | CHUYỂN VÀO _old/ | Demo Phase 1 hướng cũ (COCO, lọc xe máy) |
| `scripts/sanity_check.py` | CHUYỂN VÀO _old/ | Kiểm tra cài đặt bằng COCO, không còn cần |
| `configs/botsort_tracking.yaml` | GIỮ NGUYÊN | `PersonTracker` dùng |
| `configs/botsort_tracking_reid.yaml` | CHUYỂN VÀO _old/ | `PersonTracker` không hỗ trợ ReID (`tracker.py:26-28`) |
| `configs/data_ppe.yaml` | GIỮ NGUYÊN | Ghi nguồn dataset, `train.py` dùng |
| `configs/zones.yaml` | CHUYỂN VÀO _old/ | Vùng cấm của video thử hướng cũ; vùng kiểm tra mới sẽ thuộc bảng `gates` |
| `tests/` (4 file, 24 test) | GIỮ NGUYÊN | Sửa `test_compliance.py` khi đổi sang tên lớp |
| `weights/ppe_s/` | GIỮ NGUYÊN | Model chính (DE_TAI:37) |
| `yolo11s.pt` | GIỮ NGUYÊN | Điểm khởi đầu nếu sau này train lại |
| `yolo11n.pt`, `yolo11m.pt` | CHUYỂN VÀO _old/ | Chỉ dùng cho demo và thí nghiệm hướng cũ |
| `docs/huong_dan_train_ppe.md`, `docs/ket_qua_model_ppe.md` | GIỮ NGUYÊN | Số liệu và bằng chứng cho mục "Vì sao đổi hướng" của luận văn |
| `README.md` | SỬA LẠI | Đang mô tả hướng cũ (`README.md:1, 5, 18, 54-73, 79-96`) |
| `requirements.txt` | SỬA LẠI | Thêm thư viện backend khi tới Giai đoạn 3; nên ghim phiên bản |
| `data/raw/*.mp4` | GIỮ NGUYÊN | Video công trường hướng cũ, làm bằng chứng cho mục "Vì sao đổi hướng" |
| `runs/`, `_archive_lostlens/`, `notebooks/`, `docs/related_work/` | GIỮ NGUYÊN | Đã bị git bỏ qua hoặc đang trống, không ảnh hưởng |

---

## H. RỦI RO VÀ LỖI PHÁT HIỆN

1. **DE_TAI.md nhắc tới 2 file không tồn tại** (`ppe_monitor.py`, `clean_dataset.py`) và 3 hàm không có (`head_region`, `torso_region`, `has_item`). Trợ lý làm theo DE_TAI sẽ không tìm thấy chúng (mục F).
2. **Chỉ số lớp ghi cứng hoặc truyền tay** (`run_safety_demo.py:9, 58-60`; `README.md:65`). Nhập sai số thì kết quả sai mà không báo lỗi. Mặc định `--person-cls 0` là lớp `Mask` của best.pt.
3. **Model mặc định là `yolo11n.pt`** (`detect.py:7`). Quên `--weights` thì chạy model COCO, phần PPE tự tắt.
4. **Ngưỡng nằm trong code**, không ở file cấu hình: vùng đầu và thân (`compliance.py:19-26`), `min_inside=0.5` (`:59`), ngưỡng chứa 0.8 (`postprocess.py:10`), `conf`, `imgsz` (`run_safety_demo.py:52, 55`). Trái với DE_TAI mục 11.6.
5. **Tọa độ vùng là pixel tuyệt đối** (`zones.yaml`). Nếu độ phân giải camera điện thoại khác video dùng để vẽ, vùng sẽ lệch.
6. **Tốc độ CPU thấp:** 6.6 FPS ở imgsz 640, 2.9 FPS ở imgsz 960 (mục B.8). Trong cửa sổ 1.5 giây chỉ có khoảng 4–10 khung, ảnh hưởng điều kiện "quá ít khung hình hợp lệ". Đang suy luận ở 960, khác 640 lúc train (`run_safety_demo.py:55`, `args.yaml:9`).
7. **Không có bước gộp theo thời gian:** vi phạm tính theo từng khung, bộ đếm tính theo track ID (`run_safety_demo.py:117-120, 146`). Đây là nguyên nhân số "người vi phạm" tăng vọt trên video công trường (`docs/ket_qua_model_ppe.md`, mục ngày 2026-10-16).
8. **Model kém với vài trường hợp** (đã đo trên video công trường): nón trắng, người quay lưng, áo cam hoặc đỏ gần như không được nhận (`docs/ket_qua_model_ppe.md`). Tại cổng ở khoảng cách 3–4 m thì **CHƯA XÁC MINH**. Chỉ ghi nhận rủi ro, không đề xuất đổi model hay dataset (theo DE_TAI:37).
9. **best.pt không có trong git** (`.gitignore:13, 17`), chỉ nằm trên máy này. Bản trên Google Drive: CHƯA XÁC MINH là còn hay không.
10. **Phiên bản thư viện không ghim** (`requirements.txt:2-6` chỉ có `>=`); `torch` không được ghi trực tiếp. Cài lại có thể ra phiên bản khác. Hiện tại torch 2.14, opencv 5.0, numpy 2.5 chạy được (24 test OK).
11. **Webcam và RTSP chưa chạy thử.** Với nguồn không phải file, `cv2.VideoCapture(source)` và `Path(source).stem` (`run_safety_demo.py:79-84`) có thể không đúng: CHƯA XÁC MINH.
12. **Khóa API và mật khẩu:** không tìm thấy trong các file đã commit (lệnh `git grep` không có kết quả). Chỉ có chuỗi giữ chỗ `api_key="KEY_CUA_BAN"` trong `docs/huong_dan_train_ppe.md:74`. Không có file `.env`.
13. **README và DE_TAI.md mâu thuẫn:** README vẫn mô tả hệ thống đa camera và vùng nguy hiểm (`README.md:1, 5, 18`). `DE_TAI.md` chưa được commit.
14. **Giấy phép:** Ultralytics dùng AGPL-3.0 (`.venv/.../ultralytics/trackers/track.py:1`). Không ảnh hưởng đồ án; chỉ cần lưu ý nếu thương mại hóa.
15. Lỗi nhỏ: tham số mặc định là list có thể thay đổi, `classes=[0]` (`detect.py:18`, `tracker.py:50`). `train.py:19` mặc định `yolo11n.pt`, khác với model đã chốt là yolo11s.

---

## I. TRẢ LỜI "NHỮNG ĐIỂM TÔI CHƯA RÕ"

Danh sách trong yêu cầu **vẫn để mẫu**, chưa điền: `[điền vào đây, ví dụ: ...]`. Dưới đây là trả lời cho 3 câu ví dụ trong mẫu. Bạn bổ sung câu hỏi khác thì mình trả lời tiếp.

1. **Code đang dùng file model nào?**
   - Mặc định là `yolo11n.pt` COCO (`src/detection/detect.py:7`).
   - Model PPE `weights/ppe_s/weights/best.pt` chỉ được dùng khi truyền `--weights` (`scripts/run_safety_demo.py:51, 87`). Mọi kết quả PPE trong `docs/ket_qua_model_ppe.md` đều chạy với best.pt.
2. **Vùng cấm lưu ở đâu?**
   - File `configs/zones.yaml`, khóa là tên camera, giá trị là danh sách điểm pixel của khung hình gốc (`scripts/define_zone.py:30-38`).
   - Hiện có 4 vùng: `camera_1`, `camera_5`, `camera_6`, `camera_7`.
3. **Có backend hoặc cơ sở dữ liệu chưa?**
   - **Chưa.** Không có mã nguồn, chưa cài thư viện (mục A, D). Chỉ có dòng ghi chú ở `requirements.txt:8`.

---

## J. CÂU HỎI CẦN BẠN QUYẾT ĐỊNH

**J1. `ppe_monitor.py` và `clean_dataset.py` không có trong dự án.**
- (a) Bạn tìm và gửi 2 file đó, nếu chúng nằm ở máy khác hoặc trên Colab. Mình đối chiếu với `compliance.py` rồi chọn bản tốt hơn. *Ảnh hưởng:* mất thêm thời gian đối chiếu, nhưng không bỏ sót ý tưởng nào.
- (b) Lấy `src/ppe/compliance.py` làm bản chính thức, sửa câu tương ứng trong DE_TAI.md (`:33, :41`). *Ảnh hưởng:* không viết thêm code; giữ được 24 test và các bản sửa đã kiểm chứng trên video (tracker chỉ theo dõi người, bỏ box trùng, người cúi).
- (c) Viết mới `head_region`, `torso_region`, `has_item` đúng như DE_TAI.md mô tả. *Ảnh hưởng:* trùng chức năng với `compliance.py`, phải test lại từ đầu.

**J2. Ngưỡng vùng đầu: DE_TAI ghi "khoảng 30% phía trên", code dùng `(-0.1, 0.35)`.** Code còn có thêm ngưỡng 0.5 và quy tắc người cúi.
- (a) Giữ giá trị hiện tại, chỉ chuyển ra file cấu hình. *Ảnh hưởng:* giữ đúng hành vi đã test; người ở cổng đứng thẳng nên quy tắc người cúi gần như không kích hoạt.
- (b) Đổi thành 0.30 cho khớp DE_TAI. *Ảnh hưởng:* vùng đầu hẹp hơn; phải chạy lại test và kiểm chứng trên video ở cổng.

**J3. Chế độ cổng có giữ tracking không?**
- (a) Giữ `PersonTracker` để gom các khung của **cùng một người** trong 1.5 giây rồi bỏ phiếu. *Ảnh hưởng:* chính xác hơn khi có người đi ngang qua; phức tạp hơn, và tracker có thể đổi ID.
- (b) Bỏ tracking: mỗi khung đếm số người trong vùng kiểm tra (2 người trở lên là `NHIEU_NGUOI`), rồi bỏ phiếu đạt hoặc không đạt theo các khung. *Ảnh hưởng:* đơn giản, dễ giải thích khi bảo vệ; dựa vào giả định chỉ có 1 người đứng trong vùng.

**J4. Định dạng tọa độ vùng kiểm tra.**
- (a) Giữ pixel như hiện tại. *Ảnh hưởng:* dùng lại ngay `zones.yaml` và `define_zone.py`; vùng sẽ sai nếu đổi độ phân giải camera.
- (b) Chuyển sang tỷ lệ 0–1 so với kích thước khung. *Ảnh hưởng:* không phụ thuộc độ phân giải, hợp với việc lưu JSON trong bảng `gates` và vẽ trên web; phải sửa `define_zone.py` và `zone.py`.

**J5. Kích thước ảnh khi suy luận (imgsz).**
- (a) 640, khớp với lúc train. *Ảnh hưởng:* 6.6 FPS, khoảng 10 khung trong 1.5 giây; người đứng gần ở cổng nhiều khả năng đủ lớn (CHƯA XÁC MINH).
- (b) 960 như hiện tại. *Ảnh hưởng:* 2.9 FPS, chỉ khoảng 4 khung trong 1.5 giây; nhận người ở xa tốt hơn, nhưng ở cổng có thể không cần.
- (c) Quyết định sau khi có video quay tại cổng. *Ảnh hưởng:* cần đặt imgsz vào file cấu hình trước.

**J6. Xử lý code và tài liệu của hướng cũ (theo DE_TAI mục 11.5: không xóa, chuyển vào `_old/`).**
- (a) Chuyển các mục "CHUYỂN VÀO _old/" ở mục G ngay đầu Giai đoạn 1, và viết lại README theo DE_TAI. *Ảnh hưởng:* dự án gọn, trợ lý không nhầm hướng cũ với hướng mới.
- (b) Để nguyên tới khi xong Giai đoạn 1. *Ảnh hưởng:* không đụng gì; README tiếp tục mô tả sai hướng.

**J7. Commit `DE_TAI.md` (và `RA_SOAT.md`) vào git không?** Hiện `DE_TAI.md` chưa được track.
- (a) Commit. *Ảnh hưởng:* có lịch sử thay đổi của mô tả đề tài.
- (b) Không commit. *Ảnh hưởng:* chỉ có trên máy này.
