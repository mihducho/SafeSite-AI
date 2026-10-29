# MÔ TẢ DỰ ÁN: SafeGate

> File này là nguồn thông tin chính của dự án. Trợ lý AI phải đọc file này trước khi làm bất kỳ việc gì,
> và làm đúng theo phạm vi, quy tắc ở đây. Nếu có điểm mâu thuẫn hoặc chưa rõ thì hỏi lại, không tự đoán.
>
> **Phiên bản 2 (29/10/2026): chấm công bằng nhận diện khuôn mặt, bỏ hoàn toàn thẻ QR và kiosk quét thẻ.**
> Bản cũ (QR) chỉ còn giá trị tham khảo, mọi chỗ khác với bản này thì theo bản này.

## 1. Đề tài và mốc thời gian

**Xây dựng hệ thống quản lý và chấm công công nhân tại công trường tích hợp kiểm tra trang bị bảo hộ lao động bằng thị giác máy tính**

Tên sản phẩm: **SafeGate**. Dùng cho hai học phần: Thực tập tốt nghiệp (TTTN) và Đồ án tốt nghiệp.

- **Thi TTTN: khoảng 08/11/2026 (còn 10 ngày tính từ 29/10/2026).** Từ nay đến đó là **giai đoạn nước rút**:
  làm cho xong một bản demo chạy trọn vẹn tại cổng và một số chức năng quản lý công nhân (mục 9.1).
- Đồ án tốt nghiệp: khoảng giữa tháng 01/2027, hoàn thiện các phần còn lại (mục 9.2).

Ý tưởng một câu: **một camera tại cổng vừa nhận diện khuôn mặt để biết công nhân là ai, vừa kiểm tra mũ bảo hộ
và áo phản quang; đủ bảo hộ thì tự động ghi công.**

## 2. Lịch sử hướng đi (tóm tắt)

- Ban đầu: giám sát toàn công trường. Bỏ vì người nhỏ, ở xa, đông người, không biết ai vi phạm.
- 17/10: kiểm tra tại cổng, nhận diện công nhân bằng thẻ QR.
- **29/10: theo góp ý của giảng viên hướng dẫn, chấm công bằng khuôn mặt, dùng chung camera với module AI.**
  Lý do: QR không thực tế (quẹt thẻ hộ, mất thẻ, phải có kiosk riêng); khuôn mặt chống chấm công hộ và gắn
  kết quả kiểm tra bảo hộ trực tiếp với danh tính. Đã thử nhanh trên ảnh của bộ video `cong_gia_v1`: tìm thấy mặt ở 10/10 ảnh
  (kể cả đội mũ bảo hộ, mũ lưỡi trai, nón lá); cùng một người có độ tương đồng 0,52–0,94, hai người khác nhau 0,08–0,27;
  ở 2 ảnh "hai người đứng trước–sau" mà YOLO chỉ thấy 1 người, bộ tìm mặt vẫn thấy 2 khuôn mặt.

## 3. Hiện trạng dự án (đã có, giữ nguyên)

Thư mục dự án: `SafeSite-AI/`. Các giai đoạn 0, 1a, 1b (1b-1, 1b-2) và 2 (đánh giá rút gọn) **đã xong**.

- **Model PPE**: YOLO11s, `weights/ppe_s/weights/best.pt`, 10 lớp; chỉ dùng Person, Hardhat, Safety-Vest (tra theo tên).
- **Thuật toán kiểm tra bảo hộ chế độ cổng** (mục 6.1): `src/checkpoint/evaluate.py` (`evaluate_frames`,
  `classify_frame`, `aggregate`), `src/checkpoint/detector.py` (`YoloDetector`, `get_detector`), hàm `check()` xử lý
  từng khung ngay khi lấy được từ luồng đọc camera.
- `src/ppe/compliance.py` (`assign_ppe`, `missing_ppe`), `src/utils/postprocess.py` (`suppress_contained`),
  `src/zone/zone.py` (`zone_to_pixels`, `person_feet_point`, `point_in_zone`), luồng đọc camera chỉ giữ khung mới nhất,
  `scripts/define_zone.py` (lưu vùng dạng tỷ lệ 0–1), `scripts/make_answers.py`, `scripts/evaluate_videos.py`.
- `configs/settings.yaml`: toàn bộ tham số. Test tự động: 62 test trở lên, tất cả phải luôn chạy OK.
- Kết quả đánh giá `cong_gia_v1` (43 video, 480×854, 2 người đóng vai): đúng 38/43 (88,4%), precision vi phạm 100%,
  recall 90,9%, 0 lượt chặn nhầm. Lỗi đã biết: nón lá bị nhận là mũ bảo hộ (1/3), hai người đứng trước–sau (0/3).
  Chi tiết: `docs/ket_qua_danh_gia_cong_v1.md`.
- **Môi trường**: Windows, Python 3.13.7, ultralytics 8.4.152, torch 2.14.0 chỉ CPU, opencv-python 5.0.0.93.
  YOLO imgsz 640: khoảng 117 ms/khung trên CPU Intel Core i5-1135G7.

**Chưa có**: nhận diện khuôn mặt, backend, cơ sở dữ liệu, giao diện web.

## 4. Quyết định kỹ thuật đã chốt (không tự ý thay đổi)

**Kiểm tra bảo hộ (giữ nguyên như đã cài đặt):** model YOLO11s hiện tại, không train lại trong giai đoạn nước rút;
không dùng lớp NO-\*; luật vùng cơ thể; vùng kiểm tra dạng tỷ lệ 0–1, xét điểm chân; không dùng tracking;
bỏ phiếu nhiều khung; imgsz 640; mọi tham số trong `configs/settings.yaml`.

**Nhận diện khuôn mặt:**
- Dùng **OpenCV có sẵn**, không cài thêm thư viện nhận diện khuôn mặt:
  - Tìm mặt: **YuNet** qua `cv2.FaceDetectorYN` (giấy phép MIT).
  - Nhận dạng: **SFace** qua `cv2.FaceRecognizerSF` (giấy phép Apache 2.0), vector đặc trưng 128 chiều.
  - **Không dùng** `face_recognition`/dlib (khó cài trên Windows + Python 3.13), không dùng InsightFace
    (mô hình huấn luyện sẵn chỉ cho nghiên cứu phi thương mại), không dùng dịch vụ Docker như CompreFace.
- File mô hình đặt ở `weights/face/` (không đưa vào git), có script tải `scripts/download_face_models.py`:
  - `face_recognition_sface_2021dec.onnx`:
    `https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx`
  - `face_detection_yunet_2023mar.onnx` (đã kiểm chứng chạy được với OpenCV 5.0):
    `https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx`
  - Nếu tải được bản `face_detection_yunet_2026may.onnx` (bản đầu vào động, tài liệu OpenCV 5 dùng làm mặc định) thì dùng bản đó.
    Đường dẫn mô hình lấy từ file cấu hình.
- Cách gọi (đã chạy thử trên OpenCV 5.0):
  ```python
  det = cv2.FaceDetectorYN.create(yunet_path, "", (320, 320), 0.7, 0.3, 5000)
  det.setInputSize((w, h)); _, faces = det.detect(img)   # None hoặc mảng N×15: x, y, w, h, 10 toạ độ điểm mốc, score
  rec = cv2.FaceRecognizerSF.create(sface_path, "")
  feat = rec.feature(rec.alignCrop(img, faces[i]))       # 1×128 float32
  ```
  Tự chuẩn hoá L2 vector rồi so khớp bằng tích vô hướng numpy (cosine). Vài trăm công nhân thì so trực tiếp, không cần CSDL vector.
- **Dịch vụ AI không biết công nhân là ai**: phần AI chỉ trả về vector khuôn mặt; việc so khớp với danh sách công nhân
  nằm ở phần backend (đọc CSDL). Vector khuôn mặt chỉ lưu trong CSDL, không ghi ra file log.
- Tốc độ đo được (CPU 2 nhân, ảnh có 1 người): YuNet 480×854 khoảng 17 ms, 720×1280 khoảng 42 ms, 1080×1920 khoảng 103 ms;
  SFace khoảng 12 ms/khuôn mặt. Chiều rộng mặt người đứng trước camera: khoảng 70 px ở 480×854, 105 px ở 720×1280.
  → **Camera khuyến nghị: điện thoại đặt dọc, 720×1280**, cao ngang ngực–đầu, cách chỗ đứng 2,5–3 m, không ngược sáng.

**Bản demo TTTN (để kịp 10 ngày):**
- **Một ứng dụng FastAPI duy nhất** chạy trên laptop: luồng camera + vòng lặp cổng chạy trong một thread nền của ứng dụng.
  Code vẫn tách module rõ ràng (`src/` cho AI, `app/` cho backend và web) để sau này tách dịch vụ được.
- Giao diện: **trang HTML render phía server (Jinja2) + Bootstrap 5 + JavaScript thuần**. Không dùng React trong giai đoạn nước rút.
- CSDL: **SQLAlchemy 2**, chạy **MySQL 8 / MariaDB** (driver `pymysql`, cộng `cryptography` để đăng nhập MySQL 8;
  `DATABASE_URL=mysql+pymysql://...?charset=utf8mb4` trong `.env`). Máy demo: MariaDB 12.2 cổng 3307, quản lý bằng HeidiSQL.
  Code không dùng tính năng riêng của một hệ CSDL: chạy được cả SQLite và PostgreSQL chỉ bằng đổi `DATABASE_URL`.
  Test tự động dùng SQLite trong bộ nhớ; chạy lại toàn bộ test trên MySQL/MariaDB/PostgreSQL bằng biến `TEST_DATABASE_URL`
  (CSDL riêng có chữ `test` trong tên, ví dụ `test_safegate`).
- Không Docker, không phân quyền nhiều vai trò trong giai đoạn nước rút (chỉ tài khoản quản trị).
- Ảnh lưu thành **file**, CSDL lưu đường dẫn. Không lưu video liên tục.

## 5. Luồng tại cổng

Một **trạm chấm công** ở cổng: camera (điện thoại) + màn hình (laptop hoặc màn hình phụ) + loa. Có vạch đứng và vạch chờ.

1. Camera bật liên tục. Màn hình cổng hiện hình trực tiếp, vùng kiểm tra và dòng chữ "Mời đứng vào vị trí, nhìn vào camera".
2. **Chờ (CHO):** chạy YuNet trên khung đã thu nhỏ (cạnh dài 640 px), tối đa 10 lần/giây. Khi có khuôn mặt đủ lớn
   trong vùng (mục 6.2) xuất hiện liên tiếp `trigger_frames` khung (mặc định 3) → bắt đầu một lượt.
3. **Kiểm tra (KIEM_TRA), trong `timeout` giây (mặc định 1,5):** với mỗi khung mới nhất:
   - chạy kiểm tra bảo hộ như hiện nay (`classify_frame`);
   - chạy YuNet trên khung đầy đủ; lấy vector SFace của khuôn mặt hợp lệ (mục 6.2);
   - đếm số khuôn mặt trong vùng để phát hiện nhiều người.
   Hết thời gian: tổng hợp kết quả bảo hộ (`aggregate`, giữ nguyên) và kết quả khuôn mặt, kết hợp theo mục 6.3.
4. Gửi **một lượt** sang backend: vector khuôn mặt (tối đa 5), kết quả bảo hộ, ảnh minh chứng, thời gian.
5. Backend: so khớp khuôn mặt → biết công nhân (hoặc "không nhận ra") → xác định **vào hay ra** → ghi lượt kiểm tra,
   ghi chấm công nếu đủ điều kiện (mục 7) → đẩy kết quả lên màn hình cổng và web quản lý qua WebSocket.
6. Màn hình cổng hiện kết quả vài giây và đọc thông báo bằng loa:
   - Xanh: "Xin chào {tên}. Đã ghi giờ vào 07:02" / "Đã ghi giờ ra".
   - Đỏ: "{tên}: thiếu mũ bảo hộ / thiếu áo phản quang. Chưa ghi công".
   - Vàng: "Chưa nhận diện được, mời nhìn thẳng camera" / "Mời từng người một" / "Mời đứng yên".
7. **Chờ rời đi (CHO_ROI_DI):** không bắt đầu lượt mới cho tới khi đã qua `cooldown_seconds` (mặc định 4) VÀ
   (vùng đã trống liên tục `empty_seconds` (mặc định 1,0) HOẶC kết quả lượt trước không phải "đã ghi công").
   Nhờ vậy người không đạt có thể chỉnh lại mũ, áo rồi được kiểm tra lại ngay tại chỗ, còn người đã ghi công thì không bị ghi lặp.

## 6. Thuật toán

### 6.1. Kiểm tra bảo hộ (đã cài đặt, KHÔNG sửa logic)

Xét từng khung: phát hiện 3 lớp, bỏ khung người trùng (`suppress_contained` 0,8), giữ người có điểm chân trong vùng,
phân loại khung `trong` / `nhieu_nguoi` / `khong_hop_le` (quá nhỏ, cắt đầu) / `hop_le`; khung hợp lệ thì gán mũ vào vùng đầu
(-0,1; 0,35), áo vào vùng thân (0,15; 0,7). Tổng hợp: `nhieu_nguoi` ≥ 50% → NHIEU_NGUOI; ít hơn 3 khung hợp lệ →
KHONG_CO_NGUOI hoặc KHONG_XAC_DINH; tỷ lệ có mặt từng món ≥ 0,6 là có, ≤ 0,2 là thiếu, ở giữa là không chắc →
KHONG_XAC_DINH; có món thiếu → KHONG_DAT; đủ → DAT. Trả về `ket_qua`, `thieu`, `ty_le_co_mat`, `so_khung`,
`so_khung_hop_le`, `dem_khung`, `ly_do`, `thoi_gian_ms`, `anh_jpeg`.

### 6.2. Khuôn mặt (mới, module `src/face/`)

Tách hàm thuần (nhận dữ liệu, không đọc camera) để test được bằng dữ liệu giả, giống cách làm của `evaluate_frames`.

**Trên mỗi khung trong lượt kiểm tra:**
1. YuNet trên khung đầy đủ, ngưỡng `face.score_threshold` (mặc định 0,7).
2. **Mặt của người đang kiểm tra**: tâm khuôn mặt nằm trong **vùng đầu** (dùng lại tham số vùng đầu của `compliance`)
   của người có điểm chân trong vùng kiểm tra, và chiều rộng mặt ≥ `face.min_face_px` (mặc định 50).
   Nếu có nhiều người trong vùng thì lấy người lớn nhất. Mặt không gắn được với người nào trong vùng thì **không dùng để nhận dạng**
   (chặn trường hợp giơ ảnh, điện thoại có ảnh người khác lên).
3. Lấy vector SFace của mặt đó (`alignCrop` + `feature`), chuẩn hoá L2, kèm điểm chất lượng = score YuNet × min(1, rộng/100).
4. **Đếm mặt trong vùng** để phát hiện nhiều người: mặt có tâm nằm trong khoảng x của vùng kiểm tra (từ x nhỏ nhất đến x lớn nhất
   của đa giác), chiều rộng ≥ `face.multi_min_px` (mặc định 40) và ≥ `face.multi_min_ratio` × mặt lớn nhất (mặc định 0,7).
   Điều kiện tỷ lệ để người đứng xếp hàng xa phía sau không bị tính.

**Tổng hợp cả lượt:**
- `vectors`: tối đa `face.max_vectors` (mặc định 5) vector có chất lượng cao nhất.
- `so_khung_co_mat`, `ty_le_khung_nhieu_mat` = số khung đếm được ≥ 2 mặt / tổng số khung.
- Không có vector nào → trạng thái khuôn mặt `KHONG_THAY_MAT`.

**So khớp (ở backend, `app/services/nhan_dien.py`):**
- Mỗi công nhân **đang làm** có từ 3 đến 10 mẫu khuôn mặt (vector 128 chiều).
- Điểm của một công nhân = trung bình qua các vector của lượt, mỗi vector lấy cosine lớn nhất với các mẫu của công nhân đó.
- Chọn công nhân có điểm cao nhất. **Nhận ra** nếu điểm ≥ `face.match_threshold` (mặc định 0,40) VÀ hơn công nhân thứ hai
  ít nhất `face.match_margin` (mặc định 0,05). Ngược lại → `KHONG_NHAN_RA`.
- Ghi lại điểm tương đồng vào lượt kiểm tra để xem lại và hiệu chỉnh ngưỡng.

### 6.3. Kết hợp kết quả một lượt (module `src/gate/`)

1. Nếu `ty_le_khung_nhieu_mat` ≥ `multi_person_ratio` (dùng chung ngưỡng 0,5) → ghi đè kết quả thành `NHIEU_NGUOI`,
   `ly_do = "nhieu_mat"`. Mục đích: bắt trường hợp người đứng sau bị che thân nhưng vẫn thấy mặt.
   **Không sửa `evaluate_frames`/`aggregate`**; việc ghi đè làm ở hàm kết hợp mới.
2. Các trường hợp còn lại giữ kết quả bảo hộ.
3. Kết quả gửi backend: kết quả bảo hộ (đủ các trường như 6.1) + `khuon_mat` (`vectors`, `so_khung_co_mat`,
   `ty_le_khung_nhieu_mat`, `trang_thai`) + `anh_jpeg` (vẽ khung người, khung mặt, kết quả).

Vòng lặp cổng (`GateWorker`) là **máy trạng thái** CHO → KIEM_TRA → CHO_ROI_DI → CHO như mục 5. Phần quyết định chuyển trạng thái
viết thành hàm thuần (nhận thời gian và kết quả tìm mặt) để test được không cần camera.

## 7. Quy tắc nghiệp vụ

- **Vào hay ra** theo trạng thái công nhân trong ngày: chưa có giờ vào, hoặc đã có cả giờ vào và giờ ra → lượt này là **vào**;
  đã vào mà chưa ra → lượt này là **ra**.
- **Lượt vào**: chỉ khi nhận ra công nhân VÀ kết quả bảo hộ `DAT` mới ghi giờ vào. Không đạt thì **chưa ghi công**
  (không phải mất công), bổ sung đủ rồi kiểm tra lại. Giờ vào = thời điểm lượt `DAT` đầu tiên.
- **Lượt ra**: ghi giờ ra, **không yêu cầu bảo hộ**. Nếu lượt ra cách giờ vào dưới `duplicate_minutes` (mặc định 2 phút)
  thì bỏ qua (coi là đứng lại trước camera), ghi lượt với hành động `bo_qua_trung`.
- Vào lại sau khi đã ra (ví dụ đi ăn trưa): phải kiểm tra bảo hộ lại; giữ giờ vào đầu tiên, giờ ra lấy lần ra cuối cùng.
- `KHONG_NHAN_RA` / `KHONG_THAY_MAT`: không ghi công, vẫn lưu lượt và ảnh để cán bộ xem. Cán bộ có thể **chấm công thủ công**
  trên web, **bắt buộc ghi lý do**.
- Công nhân **nghỉ việc**: không còn được nhận diện; **xoá toàn bộ mẫu khuôn mặt** (vector và ảnh mẫu) của người đó.
- Mọi lượt kiểm tra đều lưu 1 ảnh. Ảnh có thời hạn lưu cấu hình được (mặc định 90 ngày; giai đoạn nước rút chưa cần tự xoá).

**Dữ liệu khuôn mặt (Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15, Nghị định 356/2025/NĐ-CP: dữ liệu sinh trắc học là dữ liệu nhạy cảm):**
- Chỉ đăng ký khuôn mặt khi đã **ghi nhận sự đồng ý** của công nhân: ô xác nhận trên trang đăng ký, lưu thời điểm đồng ý
  và người thực hiện; nội dung ghi rõ đây là dữ liệu sinh trắc học (dữ liệu cá nhân nhạy cảm), dùng để chấm công.
- Lưu vector đặc trưng và ảnh mẫu mặt đã căn chỉnh 112×112; không lưu ảnh gốc khi đăng ký.
- Chỉ tài khoản quản trị xem, xoá được dữ liệu khuôn mặt. Có nút "Xoá dữ liệu khuôn mặt" cho từng công nhân.

### Ca làm

- **Bản demo TTTN:** một ca mặc định trong bảng `shifts` (ví dụ 07:00–17:00, nghỉ 60 phút, ân hạn 5 phút, cho vào sớm 60 phút).
  Tính: phút đi muộn (vượt ân hạn mới tính), phút về sớm, số phút làm = min(ra, kết thúc) − max(vào, bắt đầu) − **phần giao nhau
  với giờ nghỉ trưa** [`break_start`, `break_start` + `break_minutes`] (mặc định 11:30, 60 phút), không âm: làm cả ngày trừ đủ nghỉ trưa,
  vào rồi ra trong buổi sáng thì không trừ.
  Giờ vào ngoài khung [bắt đầu − 60 phút, kết thúc] → trạng thái `ngoai_ca`. Chưa có giờ ra sau giờ kết thúc ca 4 giờ → hiển thị "thiếu giờ ra".
- **Đồ án:** nhiều ca, phân ca theo tổ đội và cá nhân, ca qua đêm, tăng ca (giữ nguyên quy tắc ở bản cũ).

## 8. Kiến trúc và cấu trúc thư mục

```
SafeSite-AI/
  src/checkpoint/   (đã có) kiểm tra bảo hộ
  src/face/         (mới) face_detector.py, face_embedder.py, analyze.py (hàm thuần mục 6.2)
  src/gate/         (mới) combine.py (mục 6.3), state.py (máy trạng thái), worker.py (GateWorker, thread nền)
  app/              (mới) FastAPI
    main.py, config.py, db.py, models.py, auth.py
    services/       nhan_dien.py (so khớp), cham_cong.py (vào/ra, tính công), luot.py (xử lý một lượt), dang_ky_mat.py
    routers/        pages (HTML, giao diện dự phòng /cu), api (JSON), ws (WebSocket), stream (MJPEG), frontend (phục vụ frontend/dist)
    templates/, static/   giao diện Jinja2 (F3), nay là dự phòng ở /cu/
  frontend/         (30/10/2026) giao diện chính React + Vite; chế độ demo: build ra frontend/dist, FastAPI phục vụ ở /
  data/             anh_luot/, anh_mau_mat/ (không đưa vào git)
  configs/settings.yaml, .env (DATABASE_URL, SECRET_KEY, mật khẩu admin ban đầu)
  scripts/          download_face_models.py, enroll_from_images.py, evaluate_faces.py, seed_demo.py
  tests/
```

- `GateWorker` chạy trong thread nền khi ứng dụng khởi động; giữ một `CameraReader` dùng chung cho vòng lặp cổng,
  luồng hình trực tiếp và chức năng chụp mẫu khuôn mặt. Model YOLO, YuNet, SFace nạp một lần.
- Mỗi lượt xong, `GateWorker` gọi `app.services.luot.xu_ly_luot(...)` (ghi CSDL bằng session riêng), rồi phát sự kiện tới các
  WebSocket đang kết nối.
- Luồng hình trực tiếp: MJPEG (`multipart/x-mixed-replace`), khoảng 10 khung/giây, vẽ vùng kiểm tra; trong lúc kiểm tra thì vẽ thêm
  khung người, khung mặt.
- Nguồn hình: file video (chạy thử, có tuỳ chọn lặp lại), webcam (số), URL camera điện thoại. **Bản demo phải chạy được
  từ file video** để phòng trường hợp camera ở phòng thi có sự cố.
- Lỗi camera hoặc model: màn hình cổng báo "Hệ thống kiểm tra tạm gián đoạn, vui lòng gặp cán bộ"; web vẫn chạy, cán bộ chấm thủ công.

## 9. Phạm vi

### 9.1. Giai đoạn nước rút TTTN (đến khoảng 07/11/2026)

**Bắt buộc:**
1. Nhận diện khuôn mặt + máy trạng thái cổng + kết hợp với kiểm tra bảo hộ (mục 5, 6).
2. CSDL và xử lý lượt: so khớp, vào/ra, ghi công, chống trùng, ca mặc định (mục 7).
3. Web: đăng nhập quản trị; **quản lý công nhân** (danh sách, tìm kiếm, lọc theo tổ, thêm, sửa, cho nghỉ việc);
   **tổ đội** (thêm, sửa); **đăng ký khuôn mặt** (ghi nhận đồng ý, chụp từ camera cổng hoặc tải ảnh lên, xem và xoá mẫu);
   **màn hình cổng** (hình trực tiếp, kết quả, loa); **lịch sử lượt kiểm tra** có ảnh, lọc theo ngày, công nhân, kết quả;
   **bảng công theo ngày**; **trang tổng quan hôm nay** (số công nhân, đã vào, đang có mặt, lượt không đạt, lượt mới nhất).
4. Script đánh giá nhận diện khuôn mặt (mục 11) và số liệu thời gian chạy thực tế.

**Nên có (làm nếu kịp, theo thứ tự):** chấm công thủ công có lý do; bảng công theo tháng; xuất Excel bảng công;
xác nhận "đúng / báo nhầm" cho lượt kiểm tra; vẽ vùng kiểm tra trên web.

### 9.2. Đồ án tốt nghiệp (sau khi thi TTTN)
Phân quyền nhiều vai trò (cán bộ an toàn, tổ trưởng); nhiều ca, phân ca, ca qua đêm, tăng ca; nhiều cổng; tự xoá ảnh quá hạn;
chống giả mạo khuôn mặt bằng mô hình riêng (ví dụ MiniFASNet); train thêm cho nón lá, áo cam; so sánh SFace với ArcFace;
thông báo Zalo/Telegram; tách dịch vụ AI riêng, React nếu cần; Docker.

### 9.3. Không làm
Thẻ QR, kiosk quét thẻ, vân tay; tính lương, thuế, bảo hiểm; giám sát toàn bộ công trường; lưu tạm offline khi mất mạng.

## 10. Cơ sở dữ liệu

- `users`: id, username (duy nhất), password_hash, full_name, role (giai đoạn nước rút chỉ `admin`), is_active.
- `teams`: id, name, contractor (nhà thầu phụ), leader_name.
- `workers`: id, code (duy nhất, ví dụ CN001), full_name, phone, trade (nghề), team_id, status (`dang_lam` / `nghi_viec`),
  consent_at, consent_by (users.id), created_at. **Không còn `qr_token`.**
- `face_samples`: id, worker_id, embedding (LargeBinary, 128 × float32 = 512 byte), quality, thumb_path (ảnh mặt 112×112),
  source (`camera` / `upload`), created_at.
- `gates`: id, name, camera_source, zone (JSON, tỷ lệ 0–1), required_ppe (JSON), rotate (góc xoay hình). Giai đoạn nước rút:
  1 cổng, tạo sẵn từ cấu hình.
- `ppe_checks` (lượt kiểm tra): id, gate_id, worker_id (có thể rỗng), checked_at, face_status (`DA_NHAN_RA` / `KHONG_NHAN_RA` /
  `KHONG_THAY_MAT`), face_score, result (5 kết quả bảo hộ), missing (JSON), presence_ratio (JSON), reason, duration_ms,
  direction (`vao` / `ra` / rỗng), action (`ghi_vao` / `ghi_ra` / `khong_ghi` / `bo_qua_trung`), image_path,
  review_status (`dung` / `bao_nham`), detail (JSON: số liệu xem lại, không có vector).
- `shifts`: id, name, start_time, end_time, break_start (giờ bắt đầu nghỉ trưa), break_minutes, grace_minutes,
  early_checkin_minutes, is_overnight, is_overtime.
- `attendance`: id, worker_id, work_date, shift_id, check_in, check_out, ppe_check_id, late_minutes, early_leave_minutes,
  worked_minutes, status (`binh_thuong` / `ngoai_ca` / `cham_thu_cong`), note, updated_by, updated_at.
  Ràng buộc duy nhất (worker_id, work_date, shift_id).

Thời gian lưu theo giờ **UTC**; MySQL/MariaDB không lưu múi giờ nên dùng `DATETIME(6)` và một kiểu chung (`UTCDateTime`,
`app/db.py`) gắn lại múi giờ UTC khi đọc. `work_date` và hiển thị tính theo giờ Việt Nam (Asia/Ho_Chi_Minh).
Trên MySQL: mọi chuỗi là `VARCHAR(n)`, JSON là kiểu `JSON` (MariaDB: `LONGTEXT` có kiểm tra JSON), vector là `BLOB`, bảng InnoDB,
bộ mã `utf8mb4`. Ràng buộc duy nhất `uq_attendance_worker_ngay_ca` (worker_id, work_date, shift_id).

## 11. Đánh giá (số liệu cho báo cáo)

1. **Nhận diện trên bộ `cong_gia_v1` có sẵn:** thêm cột `nguoi` (mã người, ví dụ A, B) vào file đáp án; đăng ký mặt hai người
   **từ ảnh riêng, không lấy từ video test**; chạy lại toàn bộ luồng (khuôn mặt + bảo hộ). Báo: tỷ lệ nhận đúng người,
   nhận nhầm, không nhận ra; kết quả bảo hộ sau khi thêm luật `nhieu_mat` (đặc biệt nhóm "2 người trước–sau", và kiểm tra
   không làm hỏng các nhóm khác).
2. **Bộ `cong_gia_v2`** (quay mới, điện thoại dọc 720×1280): 5–8 người đã đăng ký + 2–3 người chưa đăng ký. Mỗi người 3–4 lượt:
   đội mũ bảo hộ, không đội mũ, đội mũ lưỡi trai hoặc nón lá, thiếu áo. Tên file: `<ma_nguoi>_<tinh_huong>_<so>.mp4`,
   người chưa đăng ký dùng mã `LA1`, `LA2`… Báo: tỷ lệ nhận đúng, **tỷ lệ người lạ bị nhận nhầm thành công nhân** (phải bằng 0
   ở ngưỡng đã chọn), ảnh hưởng của mũ, phân bố điểm tương đồng cùng người / khác người, thời gian mỗi lượt.
3. `scripts/evaluate_faces.py` chạy luồng cổng trên từng video (mô phỏng tốc độ như `evaluate_videos.py`), ghi CSV chi tiết
   và file `tom_tat.md`. Thêm tuỳ chọn quét nhiều ngưỡng `match_threshold` (0,30 → 0,60) để chọn ngưỡng.
4. **Chạy thực tế trên ứng dụng**: đo thời gian từ lúc đứng vào đến lúc có kết quả (khoảng 10 lượt), ghi trung bình, nhỏ nhất, lớn nhất.

## 12. Các giai đoạn nước rút và tiêu chí hoàn thành

Lịch dự kiến (tính từ 29/10): F1 xong 30/10 · F2 xong 01/11 · F3 xong 03/11 · F4 xong 05/11 · 06–07/11: sửa lỗi, tập demo.

**F1. Khuôn mặt + vòng lặp cổng (phần AI)**
- `scripts/download_face_models.py`; `src/face/` theo mục 6.2; `src/gate/combine.py`, `src/gate/state.py` theo mục 5, 6.3.
- `scripts/enroll_from_images.py`: đọc thư mục `anh_dang_ky/<ma_nguoi>/*.jpg`, lấy vector, lưu ra file `.npz`
  (dùng cho chạy thử và đánh giá khi chưa có CSDL).
- `scripts/run_gate.py`: chạy vòng lặp cổng trên webcam / điện thoại / file video, so khớp với file `.npz`, in và hiện kết quả
  trong cửa sổ OpenCV (bản demo dòng lệnh, phòng khi web chưa xong).
- Mở rộng đánh giá: chạy lại `cong_gia_v1` theo mục 11.1.
- Test tự động: gắn mặt với người trong vùng, loại mặt nằm ngoài vùng đầu, đếm mặt nhiều người (kể cả người xếp hàng xa không bị tính),
  chọn vector chất lượng cao, so khớp (ngưỡng, khoảng cách với người thứ hai, không nhận ra), máy trạng thái (đủ 3 khung mới bắt đầu,
  cooldown, kiểm tra lại khi chưa ghi công).
- Hoàn thành khi: test OK; chạy `run_gate.py` với webcam nhận đúng người đã đăng ký, báo không nhận ra với người chưa đăng ký;
  có bảng kết quả `cong_gia_v1` mới.

**F2. Backend + CSDL**
- `app/` theo mục 8; models theo mục 10; tạo bảng tự động khi khởi động (giai đoạn nước rút chưa cần Alembic);
  `scripts/seed_demo.py` tạo admin, 1 cổng, 1 ca mặc định, 2 tổ đội mẫu.
- Services: `nhan_dien.py`, `dang_ky_mat.py` (kiểm tra ảnh có đúng 1 mặt, đủ lớn, score ≥ 0,85), `cham_cong.py`, `luot.py`.
- Đăng nhập (session cookie, mật khẩu băm), API JSON cho công nhân, tổ đội, mẫu mặt, lượt kiểm tra, chấm công; WebSocket sự kiện.
- `GateWorker` chạy nền trong ứng dụng, gọi `xu_ly_luot`.
- **Test bắt buộc cho phần chấm công**: vào đạt → ghi giờ vào; vào không đạt → không ghi; không đạt rồi đạt → giờ vào là lượt đạt;
  ra → ghi giờ ra; ra trong 2 phút sau khi vào → bỏ qua; vào lại sau khi ra → giữ giờ vào đầu, cập nhật giờ ra lần sau;
  đi muộn trong/ngoài ân hạn; ngoài ca; người lạ không ghi; nghỉ việc → không nhận diện và mẫu mặt bị xoá.

**F3. Giao diện web**
- Bố cục chung (thanh menu: Tổng quan, Màn hình cổng, Công nhân, Tổ đội, Lịch sử kiểm tra, Bảng công), Bootstrap 5.
- Các trang theo mục 9.1. Màn hình cổng: hình trực tiếp + ô kết quả lớn, đổi màu theo kết quả; đọc thông báo bằng
  `speechSynthesis` giọng `vi-VN` nếu trình duyệt có, nếu không thì phát tiếng bíp (1 tiếng: đạt, 2 tiếng: không đạt).
  Khuyến nghị mở bằng Microsoft Edge (có giọng tiếng Việt).
- Đăng ký khuôn mặt: ô đồng ý (bắt buộc tích mới cho chụp); nút "Chụp từ camera cổng" (lấy khung hiện tại, cần đúng 1 mặt đủ lớn);
  tải nhiều ảnh lên; hiển thị số mẫu (cần ít nhất 3), ảnh mẫu, xoá từng mẫu, xoá tất cả.
- Hoàn thành khi: thao tác được toàn bộ kịch bản demo (mục 13) trên trình duyệt.

**F4. Đánh giá v2 + hoàn thiện demo**
- Chạy `evaluate_faces.py` trên `cong_gia_v2`, chọn ngưỡng, ghi `docs/ket_qua_danh_gia_khuon_mat.md`.
- Đo thời gian thực tế; chụp màn hình các trang; viết `README.md` hướng dẫn cài và chạy demo; kiểm tra chạy từ file video.
- Làm các mục "nên có" nếu còn thời gian.

## 13. Kịch bản demo trước giảng viên (khoảng 5 phút)

1. Trang tổng quan: số công nhân, tình hình hôm nay.
2. Thêm công nhân mới, tích đồng ý, chụp 3 mẫu khuôn mặt từ camera cổng.
3. Màn hình cổng: người đó đứng vào không đội mũ → đỏ "thiếu mũ bảo hộ, chưa ghi công"; đội mũ, mặc áo → xanh "đã ghi giờ vào".
4. Một người chưa đăng ký đứng vào → vàng "chưa nhận diện được".
5. Hai người cùng đứng vào → "mời từng người một".
6. Lịch sử kiểm tra (có ảnh từng lượt) và bảng công hôm nay (giờ vào, đi muộn).
7. Lượt ra → ghi giờ ra, số giờ làm.
8. Cho một công nhân nghỉ việc → mẫu khuôn mặt bị xoá, đứng vào không còn được nhận ra.
Dự phòng: chạy nguồn hình từ file video đã quay sẵn.

## 14. Quy tắc làm việc cho trợ lý AI

1. **Giai đoạn nước rút**: làm lần lượt F1 → F4. Hết mỗi giai đoạn: tóm tắt ngắn đã làm gì, cách chạy thử, kết quả, rồi **dừng chờ tôi
   xác nhận**. Trong một giai đoạn, tự quyết các chi tiết nhỏ (tên hàm, bố cục trang) để làm nhanh; ghi lại các quyết định đó trong tóm tắt.
2. **Đọc code hiện có trước khi viết.** Tái sử dụng (`classify_frame`, `aggregate`, `assign_ppe`, `zone_to_pixels`, luồng đọc camera,
   `evaluate_videos.py`…), không viết lại những gì đã chạy được. **Không sửa logic kiểm tra bảo hộ đã đánh giá.**
3. **Không tự ý** đổi model, train lại, thêm thư viện lớn ngoài danh sách (FastAPI, uvicorn, SQLAlchemy, psycopg, Jinja2,
   python-multipart, passlib/bcrypt hoặc hashlib, itsdangerous, openpyxl). Cần thêm thì hỏi.
4. **Chạy thử code sau khi viết.** Không báo "xong" nếu chưa chạy được thật. Không chạy được thì nói rõ lỗi.
5. Không xoá file cũ; cần bỏ thì chuyển vào `_old/` và báo tôi.
6. Tham số đặt trong `configs/settings.yaml` (mục `face:`, `gate:`, `attendance:`), bí mật đặt trong `.env`. Không hard-code.
7. Giải thích ngắn gọn bằng tiếng Việt. Tôi cần hiểu code để bảo vệ.
8. **Mọi test hiện có phải vẫn chạy OK**; code mới phải có test (phần chấm công và so khớp bắt buộc).
9. Commit sau mỗi giai đoạn với thông điệp rõ ràng. Không đưa trọng số model, ảnh, video, `.env` vào git.
10. Khi `DE_TAI.md` mâu thuẫn với code, dừng lại và hỏi tôi.

## 15. Tham số cấu hình mới (giá trị ban đầu)

```yaml
face:
  detector_model: weights/face/face_detection_yunet_2023mar.onnx
  recognizer_model: weights/face/face_recognition_sface_2021dec.onnx
  score_threshold: 0.7        # YuNet
  enroll_min_score: 0.85      # ảnh đăng ký
  min_face_px: 50             # chiều rộng mặt tối thiểu để nhận dạng
  multi_min_px: 40
  multi_min_ratio: 0.7
  max_vectors: 5
  match_threshold: 0.40       # OpenCV khuyến nghị 0.363 trên LFW; hiệu chỉnh bằng mục 11
  match_margin: 0.05
  min_samples: 3
  max_samples: 10
gate:
  idle_long_side: 640
  idle_max_fps: 10
  trigger_frames: 3
  cooldown_seconds: 4
  empty_seconds: 1.0
attendance:
  duplicate_minutes: 2
  missing_checkout_hours: 4
  timezone: Asia/Ho_Chi_Minh
```

## 16. Nhật ký quyết định

**2026-10-17 (sau rà soát):** dùng `src/ppe/compliance.py` làm bản chính thức; giữ vùng đầu (-0.1, 0.35); chế độ cổng không tracking;
vùng kiểm tra tỷ lệ 0–1; chuyển code cũ vào `_old/`.

**2026-10-17 (sau 1b-1):** chấp nhận tham số `detector` không bắt buộc, `zone_to_pixels`, `missing_code`, `dem_khung`, `ly_do`,
gán đồ bảo hộ có xét người ngoài vùng; `check` xử lý khung ngay khi lấy được.

**2026-10-21 (sau đánh giá `cong_gia_v1`):** chốt imgsz 640; nón lá và hai người trước–sau là lỗi đã biết, xử lý trong đồ án.

**2026-10-29 (góp ý của giảng viên, còn 10 ngày tới thi TTTN):**
- Bỏ thẻ QR và kiosk quét thẻ; **chấm công bằng khuôn mặt, dùng chung camera với module AI**.
- Dùng YuNet + SFace có sẵn trong OpenCV; so khớp ở backend; ghi nhận đồng ý và xoá mẫu mặt khi nghỉ việc.
- Thêm luật `nhieu_mat` (đếm khuôn mặt) để bắt trường hợp hai người đứng trước–sau, không sửa thuật toán bảo hộ cũ.
- Bản demo: một ứng dụng FastAPI + Jinja2 + Bootstrap, PostgreSQL qua SQLAlchemy; React, Docker, phân quyền để sang đồ án.
- Làm thêm các chức năng quản lý công nhân: công nhân, tổ đội, đăng ký khuôn mặt, lịch sử, bảng công, tổng quan.

**2026-10-29 (sau F1, commit 73107d0):**
- So khớp viết thành hàm thuần trong `src/face/match.py` (`match`, `score_workers`); `app/services/nhan_dien.py` (F2) đọc mẫu
  từ CSDL rồi gọi hàm này. Thêm `src/face/match.py`, `src/face/enroll.py` (kiểm tra ảnh mẫu), `src/gate/round.py` (một lượt:
  `FrameEvaluator` giữ nguyên + phần khuôn mặt) ngoài các file ở mục 8.
- Trạng thái CHO chưa chạy YOLO nên "có mặt trong vùng" = tâm mặt nằm trong khoảng x của vùng kiểm tra và rộng ≥ `min_face_px`.
- Giữ YuNet `2023mar`: bản `2026may` cho kết quả giống hệt trên ảnh thử nhưng chậm hơn (480×854: 28 ms so với 20 ms).
- Thêm `face.opencv_threads: 4`: ultralytics tự đặt OpenCV về 1 luồng khi nạp, làm YuNet/SFace chậm khoảng 2 lần.
- Cột `nguoi` (mã người A/B) trong file đáp án là cột không bắt buộc; ghi lại file đáp án vẫn giữ giá trị đã điền tay.
- `cong_gia_v1` (cùng 18 khung như lần đánh giá chính thức): bảo hộ 38/43 → 40/43 sau luật `nhieu_mat`
  (`hai_nguoi_dungsau_01`, `_02` đúng), không nhóm nào kém đi. Thời gian một lượt 1,5–1,7 giây (8–12 khung),
  từ lúc thấy mặt đến lúc có kết quả khoảng 1,8 giây.
- **Giữ `face.multi_min_ratio = 0.7`, không hạ xuống 0,6**: không chỉnh ngưỡng theo đúng bộ dữ liệu đang dùng để đánh giá;
  người xếp hàng cách 1,5–2 m phía sau có mặt bằng khoảng 0,6–0,67 mặt người đứng trước, hạ ngưỡng dễ báo nhầm NHIEU_NGUOI.
  `hai_nguoi_dungsau_03` (mặt người sau bằng 0,64–0,70 mặt người trước) ghi là **hạn chế đã biết**; quay thêm trường hợp
  "người xếp hàng sau vạch chờ" ở bộ `cong_gia_v2` rồi mới xem lại ngưỡng này.
- Tỷ lệ nhận đúng người trên `cong_gia_v1`: người dùng tự điền cột `nguoi` và chuẩn bị ảnh đăng ký riêng của A/B rồi chạy
  `evaluate_faces.py --enroll-dir`. Mẫu chụp bằng webcam laptop cho điểm ở cổng thấp hơn (0,40–0,60) → đăng ký bằng camera cổng.

**2026-10-29 (sau F2, commit 3352ac0), đã đồng ý:**
- Vào lại sau khi đã ra: phải đạt bảo hộ; giữ giờ vào đầu tiên, xoá giờ ra cũ (đang có mặt), lần ra sau ghi giờ ra mới.
  Chống trùng 2 phút tính từ **lần vào gần nhất** trong ngày (không phải giờ vào đầu tiên).
- Lượt ra không xét bảo hộ, trừ `NHIEU_NGUOI` và `KHONG_CO_NGUOI` (không ghi công cả vào lẫn ra).
- Đi muộn: vượt ân hạn thì tính toàn bộ số phút từ giờ bắt đầu ca (vào 07:06 → muộn 6 phút).
- Màn hình cổng: `bo_qua_trung` màu xanh "…đã ghi giờ vào HH:MM, không ghi lặp", sau đó chờ người rời đi; lượt không đạt
  hoặc không nhận ra thì cho kiểm tra lại ngay tại chỗ. Vào lại hiện "Đã ghi vào lại HH:MM".
- Chỉ so khớp công nhân có ≥ `face.min_samples` (3) mẫu.
- Thêm cột `gates.rotate` (góc xoay hình) và `ppe_checks.detail` (số liệu xem lại, không có vector); chấm công thủ công
  ghi thêm 1 dòng vào `note` (giờ, người sửa, lý do) để giữ lịch sử.
- Nguồn hình: `GATE_SOURCE` trong `.env`, không có thì `gates.camera_source`; đổi bằng `seed_demo.py --source` +
  `POST /api/cong/khoi-dong-lai`. URL có mật khẩu không lưu vào CSDL.
- Mật khẩu băm bằng `hashlib` (PBKDF2-SHA256, 600 000 vòng), không dùng passlib.
- Thêm 2 gói ngoài danh sách mục 14.3: `websockets` (uvicorn cần để chạy WebSocket), `tzdata` (dữ liệu múi giờ trên Windows).
- Thêm 3 API: cho đi làm lại (phải ghi nhận đồng ý lại từ đầu), khởi động lại cổng, nội dung câu đồng ý.
- Code F1 chỉ thêm, không sửa logic bảo hộ: `GateWorker` nhận `required_ppe`, `GateRound.last` (khung vừa xử lý, để vẽ luồng hình),
  `sample_from_image(long_side=...)`.

**2026-10-29 (trước F3, theo yêu cầu của tôi):**
- **CSDL chuyển sang MySQL 8 / MariaDB** (tôi thành thạo MySQL nhất, cần trả lời được khi bảo vệ); không dùng PostgreSQL cài trên máy.
  Máy demo: MariaDB 12.2.2, cổng 3307, CSDL `safegate` (utf8mb4), tài khoản `safegate`. Driver `pymysql` + `cryptography`.
  Code vẫn chạy được trên SQLite và PostgreSQL (toàn bộ test đã chạy trên cả MariaDB 12.2 và PostgreSQL 17).
- Giờ lưu UTC bằng một kiểu chung `UTCDateTime` (MySQL: `DATETIME(6)`, đọc ra gắn lại múi giờ UTC).
- Test trên MySQL thật: biến môi trường `TEST_DATABASE_URL` trỏ tới CSDL riêng có chữ `test` trong tên (máy demo: `test_safegate`,
  MariaDB mặc định cho phép tạo CSDL tên `test_...`); test tự xoá sạch bảng nên có chốt chặn không chạy nhầm lên CSDL thật.
- Dữ liệu thử CN001 chép từ `data/safegate.db` (SQLite, giữ lại làm bản dự phòng) sang MariaDB; giữ tới hết F3.
  `seed_demo.py --reset` xoá sạch CSDL, `data/anh_luot/`, `data/anh_mau_mat/` rồi tạo lại dữ liệu ban đầu (chạy trước buổi demo).
- Số phút làm chỉ trừ phần giao nhau với giờ nghỉ trưa (cột mới `shifts.break_start`, mặc định 11:30): vào 12:12, ra 12:15 → 0 phút
  (nằm trong giờ nghỉ); làm buổi sáng 08:00–11:00 → 180 phút (không trừ). `seed_demo.py --ca 07:00-17:00` để chỉnh giờ ca hôm demo.

**2026-10-30 (theo yêu cầu của tôi): giao diện chính chuyển sang React** (thư mục `frontend/`, tôi dựng bằng Antigravity),
mọi chức năng chạy bằng dữ liệu thật của backend; không đổi logic AI, chấm công, luật nghiệp vụ.
- Giao diện Jinja2 (F3) giữ làm dự phòng, chuyển sang `/cu/...` (đăng nhập `/cu/login`). `/docs`, `/openapi.json` giữ ở gốc;
  chưa đăng nhập mà mở `/docs` thì về trang đăng nhập của giao diện React (`/login?next=/docs`).
- Chế độ phát triển: `npm run dev` (cổng 3000), Vite chuyển `/api`, `/ws`, `/stream`, `/docs`, `/cu` sang cổng 8000 (không bật CORS).
  Chế độ demo: `npm run build`, FastAPI phục vụ `frontend/dist` ở `/` (đường dẫn của giao diện trả `index.html`; tham số mới
  `paths.frontend_dist`), hôm thi chỉ chạy `uvicorn`, không cần Node. Chưa build thì `/` chuyển sang `/cu/`.
- Thêm tối thiểu cho giao diện React (có test): API `GET /api/cau-hinh-web` (tham số settings.yaml mà Jinja2 truyền qua template:
  ngày hôm nay theo giờ Việt Nam, số mẫu tối thiểu/tối đa, số giây hiện kết quả, số dòng mỗi trang); trường `luot_theo_gio` trong
  `GET /api/tong-quan` (biểu đồ số lượt theo giờ hôm nay: đạt / không đạt / khác).
- Font Inter để trong bản build (`@fontsource-variable/inter`, OFL), bỏ Google Fonts. Kiểm thử giao diện bằng Playwright
  (`npm run test:ui`, chạy trên Edge có sẵn).
