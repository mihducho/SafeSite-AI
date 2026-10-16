# MÔ TẢ DỰ ÁN: SafeSite-AI

> File này là nguồn thông tin chính của dự án. Trợ lý AI phải đọc file này trước khi làm bất kỳ việc gì,
> và làm đúng theo phạm vi, quy tắc ở đây. Nếu có điểm mâu thuẫn hoặc chưa rõ thì hỏi lại, không tự đoán.

## 1. Tên đề tài

**Xây dựng hệ thống quản lý và chấm công công nhân tại công trường tích hợp kiểm tra trang bị bảo hộ lao động bằng thị giác máy tính**

Tên sản phẩm: **SafeSite-AI**. Đồ án tốt nghiệp ngành CNTT, thời gian còn khoảng 3 tháng.

## 2. Vì sao đổi hướng

Hướng cũ: giám sát toàn bộ công trường bằng camera, phát hiện người không đội mũ/không mặc áo bảo hộ, có vẽ vùng cấm.

Vấn đề của hướng cũ:
- Model train tốt trên dataset (mAP50 ≈ 0.83, precision ≈ 0.92) nhưng chạy trên video camera công trường thì sai nhiều:
  người nhỏ, ở xa, bị che khuất, góc cao, đông người.
- Báo vi phạm từng người ở công trường đông người gây quá nhiều cảnh báo, không thực tế.
- Không biết người vi phạm là ai.

Hướng mới: **kiểm tra tại cổng ra vào**. Mỗi lần chỉ 1 người, đứng gần camera (3–4 m), nhìn rõ.
Bài toán AI dễ hơn nhiều, và gắn được với chấm công vì biết người đó là ai qua thẻ QR.

## 3. Hiện trạng dự án (đã có)

Theo `docs/RA_SOAT.md` (rà soát ngày 2026-10-16, commit `d1e9342`). Thư mục dự án: `SafeSite-AI/`.

**Model**
- YOLO11s, train trên Colab, dataset Roboflow "construction-site-safety-rmep1" (workspace 007-kd2zw, version 3),
  imgsz=640, epochs=100. File trọng số: **`weights/ppe_s/weights/best.pt`** (không nằm trong git).
- 10 lớp (đã kiểm chứng bằng `model.names`): 0 Mask, 1 Safety-Vest, 2 NO-Safety-Vest, 3 Person, 4 machinery,
  5 Safety-Cone, 6 vehicle, 7 Hardhat, 8 NO-Mask, 9 NO-Hardhat.
- Điểm yếu đã ghi nhận trên video công trường (`docs/ket_qua_model_ppe.md`): **mũ trắng, người quay lưng,
  áo cam hoặc đỏ** gần như không được nhận. Tại cổng (3–4 m, đứng đối diện camera): CHƯA XÁC MINH.

**Code tái sử dụng được** (đã có 24 test, chạy OK)
- `src/ppe/compliance.py`: `assign_ppe`, `missing_ppe`. Gán mỗi box mũ/áo cho một người theo vùng đầu/vùng thân;
  có quy tắc người cúi (box thấp hơn rộng thì dùng cả box).
- `src/utils/postprocess.py`: `suppress_contained` (bỏ box người nằm trong box người lớn hơn).
- `src/zone/zone.py`: `point_in_zone`, `person_feet_point` (kiểm tra điểm chân trong đa giác).
- `src/tracking/tracker.py`: `PersonTracker` (BoT-SORT, chỉ theo dõi người). Chế độ cổng KHÔNG dùng (xem mục 4).
- `src/utils/visualize.py`: hàm vẽ khung và chữ.
- `scripts/define_zone.py`: vẽ đa giác bằng cửa sổ OpenCV. `scripts/extract_frames.py`: cắt khung từ video.

**Môi trường**: Python 3.13.7 (Windows), ultralytics 8.4.152, torch 2.14.0 **chỉ CPU** (không có CUDA),
opencv-python 5.0.0.93. Tốc độ trên CPU (video 1280×720): **6.6 FPS ở imgsz 640**, 2.9 FPS ở imgsz 960.

**Chưa có**: backend, cơ sở dữ liệu, frontend, Docker, quét QR, chế độ cổng, lưu ảnh từng lượt.
Code hướng cũ ghi cả video kết quả, xét vi phạm theo từng khung, không gộp theo thời gian.

## 4. Quyết định kỹ thuật đã chốt (không tự ý thay đổi)

- **Giữ model YOLO11s hiện tại (`weights/ppe_s/weights/best.pt`). Không đổi model, không tìm dataset mới.**
  Chưa train lại cho đến khi có kết quả đánh giá tại cổng (Giai đoạn 2). Nếu khi đó model kém ở vài trường hợp cụ thể
  (ví dụ mũ trắng, áo cam), hướng xử lý là bổ sung ảnh đúng trường hợp đó rồi train thêm, và phải được tôi duyệt trước.
- Đường dẫn model mặc định lấy từ **file cấu hình**, không còn mặc định `yolo11n.pt`.
- **Không dùng các lớp NO-\*** (NO-Hardhat, NO-Safety-Vest, NO-Mask). Chỉ dùng Person, Hardhat, Safety-Vest.
  **Tra chỉ số lớp theo TÊN** trong `model.names` (Person, Hardhat, Safety-Vest), bỏ các tham số `--person-cls`,
  `--hardhat-cls`, `--vest-cls`. Không tìm thấy tên lớp thì báo lỗi rõ ràng và dừng.
- Vi phạm xác định bằng **luật vùng cơ thể**, dùng lại nguyên `src/ppe/compliance.py` (`assign_ppe`, `missing_ppe`).
  **Giữ giá trị hiện tại**: vùng đầu (-0.1, 0.35), vùng thân (0.15, 0.7), tỷ lệ nằm trong vùng tối thiểu 0.5,
  ngưỡng chứa của `suppress_contained` 0.8; **chuyển tất cả ra file cấu hình**. Không viết hàm mới trùng chức năng.
- **Vùng kiểm tra** dùng lại `point_in_zone`, `person_feet_point` (kiểm tra điểm chân).
  **Tọa độ lưu dạng tỷ lệ 0–1** so với kích thước khung hình (không còn pixel tuyệt đối), để không phụ thuộc
  độ phân giải camera và để lưu JSON trong bảng `gates`, vẽ trên web. Quy đổi sang pixel lúc chạy.
- **Chế độ cổng không dùng tracking.** Xét từng khung rồi bỏ phiếu theo mục "Thuật toán kiểm tra" (mục 5).
- **imgsz suy luận mặc định 640** (khớp lúc train, nhanh hơn trên CPU), đặt trong file cấu hình.
  Giai đoạn 2 so sánh thêm 960 rồi mới chốt.
- Nhận diện công nhân bằng **mã QR** trên thẻ. Không dùng nhận diện khuôn mặt, không dùng vân tay.
- Nội dung mã QR là **chuỗi ngẫu nhiên (UUID)** lưu trong cơ sở dữ liệu, KHÔNG phải mã công nhân dạng CN001.
- Ảnh lưu thành **file**, cơ sở dữ liệu chỉ lưu **đường dẫn ảnh**. Không lưu video liên tục.
- Bản demo: **chạy tất cả trên 1 laptop** (AI, backend, cơ sở dữ liệu, kiosk). Điện thoại cũ làm camera IP (RTSP/HTTP),
  webcam laptop dùng để quét QR.

## 5. Luồng tại cổng (khi vào ca)

1. Camera bật liên tục, gửi hình về dịch vụ AI. Màn hình kiosk hiện "Mời quét thẻ".
2. Công nhân quét QR ở kiosk. Backend kiểm tra thẻ còn hiệu lực, lấy tên và ảnh hồ sơ.
3. Backend yêu cầu dịch vụ AI kiểm tra người trong vùng kiểm tra, trong khoảng 1.5 giây.
4. Dịch vụ AI trả về một trong các kết quả:
   - `DAT`: đủ mũ và áo.
   - `KHONG_DAT`: kèm danh sách thiếu (`thieu_mu`, `thieu_ao`).
   - `KHONG_XAC_DINH`: người quá nhỏ, bị cắt khung, quá ít khung hình hợp lệ.
   - `NHIEU_NGUOI`: có từ 2 người trở lên trong vùng kiểm tra.
   - `KHONG_CO_NGUOI`: không thấy ai trong vùng.
   Kèm 1 ảnh chụp tại thời điểm kiểm tra.
5. Backend lưu lượt kiểm tra. Nếu `DAT` thì ghi giờ vào ca.
6. Kiosk hiển thị kết quả (xanh / đỏ / vàng) và phát loa. Sau vài giây quay về màn hình chờ.
7. Web quản lý nhận lượt quét mới ngay lập tức qua WebSocket.

Khi ra về: quét QR để ghi giờ ra, không kiểm tra bảo hộ. Nếu người đó đang ở trạng thái "đã vào" thì lần quét này là "ra".

### Thuật toán kiểm tra của dịch vụ AI (chế độ cổng)

Tách làm 2 hàm:
- `evaluate_frames(frames, zone, required_ppe, config) -> dict`: **hàm thuần**, nhận danh sách khung hình,
  không đọc camera. Dùng cho cả kiểm tra thật, script chạy thử trên video, và test tự động.
- `check(timeout)`: **xử lý từng khung ngay khi lấy được** từ luồng đọc camera (không gom đủ `timeout` giây rồi mới xử lý),
  cho đến khi hết `timeout`, rồi tổng hợp. Dùng chung `classify_frame` và `aggregate` với `evaluate_frames`
  để hai đường chạy cho kết quả giống nhau. Tổng thời gian một lượt kiểm tra ≈ `timeout`.

**Bước 1. Xét từng khung:**
1. Detect, chỉ giữ 3 lớp Person, Hardhat, Safety-Vest; bỏ box người trùng bằng `suppress_contained`.
2. Chỉ giữ người có **điểm chân nằm trong vùng kiểm tra**.
3. Phân loại khung: 0 người → `trong`; từ 2 người → `nhieu_nguoi`; đúng 1 người → xét tiếp.
4. Khung 1 người là **không hợp lệ** nếu: chiều cao box người nhỏ hơn ngưỡng (pixel, cấu hình được),
   hoặc mép trên box chạm mép trên khung hình (đầu bị cắt, không xét được mũ).
5. Khung 1 người hợp lệ: dùng `assign_ppe` để ghi nhận có mũ / có áo trong khung đó. Khi gán, xét **tất cả người
   trong khung** (kể cả người đứng ngoài vùng), để mũ/áo của người đứng sát bên ngoài không bị gán nhầm cho người trong vùng.

**Bước 2. Tổng hợp** (các ngưỡng là giá trị ban đầu, đặt trong file cấu hình, hiệu chỉnh ở Giai đoạn 2):
1. Quá nửa số khung là `nhieu_nguoi` → `NHIEU_NGUOI`.
2. Số khung hợp lệ dưới `min_valid_frames` (mặc định 3): nếu quá nửa số khung là `trong` → `KHONG_CO_NGUOI`,
   ngược lại → `KHONG_XAC_DINH`.
3. Với mỗi món bảo hộ bắt buộc, tính **tỷ lệ có mặt** = số khung hợp lệ thấy món đó / số khung hợp lệ:
   - tỷ lệ ≥ `present_ratio` (mặc định 0.6) → **có**;
   - tỷ lệ ≤ `absent_ratio` (mặc định 0.2) → **thiếu**;
   - ở giữa → **không chắc**.
4. Có món nào **không chắc** → `KHONG_XAC_DINH` (mời đứng yên và quét lại).
   Ngược lại, có món **thiếu** → `KHONG_DAT` kèm danh sách thiếu. Tất cả **có** → `DAT`.

**Kết quả trả về** gồm: `ket_qua`, `thieu` (danh sách thiếu), `ty_le_co_mat` của từng món, `so_khung`, `so_khung_hop_le`,
`dem_khung` (số khung theo từng loại), `ly_do` (`it_khung_hop_le` hoặc `khong_chac` khi KHONG_XAC_DINH, để kiosk báo đúng lý do),
`thoi_gian_ms`, và `anh_jpeg`: khung hợp lệ có người lớn nhất, có vẽ khung nhận diện; nếu không có khung hợp lệ thì lấy
khung có người lớn nhất; không có người nào thì lấy khung cuối.

`zone=None` thì xét cả khung: **chỉ dùng khi chạy thử**. Khi chạy thật, backend luôn gửi vùng kiểm tra.

Lý do có vùng "không chắc": tại cổng, quét lại rất rẻ (vài giây), còn kết luận sai thì hoặc chặn nhầm người đủ đồ,
hoặc cho người thiếu đồ đi qua. Khi không chắc, hệ thống yêu cầu quét lại thay vì đoán.

## 6. Quy tắc nghiệp vụ

- Thiếu bảo hộ thì **chưa ghi công**, không phải mất công. Bổ sung đủ rồi quét lại.
- Quét trùng trong vòng 2 phút thì bỏ qua.
- Không có ca hôm nay: vẫn ghi nhận, đánh dấu "ngoài ca" để quản lý duyệt.
- Quên quét lúc ra: cuối ngày đánh dấu "thiếu giờ ra".
- Quên/mất thẻ: cán bộ chấm công thủ công trên web, **bắt buộc ghi lý do**.
- Mất thẻ: cấp lại mã mới, mã cũ hết hiệu lực. Nghỉ việc: khóa thẻ.
- Chụp ảnh cho **mọi lượt quét** (kể cả đạt) để chống quẹt thẻ hộ. Ảnh có thời hạn lưu cấu hình được (mặc định 90 ngày).
- Danh sách đồ bảo hộ bắt buộc **cấu hình được** (bật/tắt kiểm tra áo).
- **Một kiosk dùng chung cho cả vào và ra.** Hệ thống tự nhận biết vào hay ra theo trạng thái hiện tại của công nhân.

### Ca làm (thuộc phần lõi, bắt buộc)

- Mỗi ca có: tên, giờ bắt đầu, giờ kết thúc, thời gian nghỉ giữa ca (phút), số phút ân hạn đi muộn (mặc định 5),
  được quét vào sớm tối đa bao nhiêu phút trước giờ bắt đầu (mặc định 60), có phải ca qua đêm không, có phải ca tăng ca không.
- Phân ca: gán ca cho **tổ đội** theo khoảng ngày; có thể ghi đè cho **từng công nhân** theo ngày.
  Một công nhân có thể có nhiều ca trong một ngày (ví dụ ca ngày + ca tăng ca tối).
- Khi quét vào: tìm ca của công nhân sao cho thời điểm quét nằm trong khung [giờ bắt đầu − quét sớm tối đa, giờ kết thúc].
  Không tìm thấy ca nào → ghi nhận với trạng thái "ngoài ca", chờ quản lý duyệt.
- **Giờ vào ca = thời điểm của lượt kiểm tra ĐẠT đầu tiên** trong ca đó. Các lượt KHÔNG ĐẠT trước đó không tính là giờ vào.
- Đi muộn (phút) = giờ vào − giờ bắt đầu ca, nếu số phút này lớn hơn số phút ân hạn; ngược lại bằng 0.
- Về sớm (phút) = giờ kết thúc ca − giờ ra, nếu lớn hơn 0.
- Số phút làm = min(giờ ra, giờ kết thúc) − max(giờ vào, giờ bắt đầu) − nghỉ giữa ca, không âm.
- **Tăng ca chỉ tính khi công nhân được phân vào một ca có đánh dấu tăng ca.** Ở lại muộn mà không được phân thì không tự tính.
- Ra ngoài giữa ca rồi quay lại (ví dụ đi ăn trưa): **lần vào lại vẫn phải kiểm tra bảo hộ**. Giữ giờ vào đầu tiên,
  giờ ra lấy lần quét ra cuối cùng. Thời gian ra ngoài không trừ riêng (đã trừ bằng nghỉ giữa ca).
- Ca qua đêm: bản ghi công thuộc về **ngày bắt đầu ca**.
- Quá giờ kết thúc ca một khoảng thời gian cấu hình được (mặc định 4 giờ) mà chưa quét ra → trạng thái "thiếu giờ ra".

## 7. Phạm vi

**Phần lõi (bắt buộc, ưu tiên làm trước):**
- M1. Tài khoản và phân quyền: quản trị viên, cán bộ an toàn, tổ trưởng (tổ trưởng chỉ xem dữ liệu tổ mình).
- M2. Công nhân và tổ đội: hồ sơ, cấp thẻ QR, in thẻ PDF, cấp lại, khóa thẻ.
- M3. Cổng và cấu hình: địa chỉ camera, vẽ vùng kiểm tra, đồ bảo hộ bắt buộc, khung giờ hoạt động, thời hạn lưu ảnh.
- M4. Dịch vụ AI chế độ cổng kiểm tra.
- M5. Kiosk và chấm công vào/ra (một kiosk dùng chung), chấm công thủ công có ghi lý do.
- **M6. Ca làm: định nghĩa ca, phân ca theo tổ đội và theo cá nhân, tính đi muộn, về sớm, số giờ làm, tăng ca.**
- M7. Lịch sử lượt quét có ảnh, lọc theo ngày/người/kết quả; cán bộ an toàn xác nhận "đúng/báo nhầm".
- M8. Tổng quan và báo cáo cơ bản: trang tổng quan hôm nay (đã vào, đang có mặt, số lượt không đạt, tỷ lệ tuân thủ,
  lượt quét mới nhất tự cập nhật), bảng công theo tháng, xuất Excel.

**Phần mở rộng (chỉ làm khi phần lõi đã xong và chạy ổn):**
- Thống kê nâng cao: tỷ lệ tuân thủ theo giờ trong ngày, theo tổ đội, xu hướng theo tuần.
- Công nhân tự tra cứu công của mình (ví dụ quét thẻ ở kiosk để xem số công tháng này).
- Thông báo Telegram/Zalo cho tổ trưởng, cán bộ an toàn.
- Dùng mô hình AI đa phương thức làm "ý kiến thứ hai" khi kết quả là KHONG_XAC_DINH.

**Không làm:**
- Tính lương, thuế, bảo hiểm.
- Nhận diện khuôn mặt, vân tay.
- Giám sát toàn bộ công trường, cảnh báo đông người.
- Lưu tạm offline khi mất mạng (chỉ ghi ở hướng phát triển).

## 8. Kiến trúc và công nghệ

Nếu dự án đã có sẵn công nghệ khác, giữ nguyên và báo lại cho tôi, không tự ý thay.

| Thành phần | Công nghệ đề xuất |
|---|---|
| Dịch vụ AI | Python, Ultralytics YOLO11s, OpenCV |
| Backend | FastAPI, SQLAlchemy, PostgreSQL, WebSocket |
| Frontend | React (Vite): trang kiosk + web quản lý |
| Quét QR | thư viện `html5-qrcode` trên trang kiosk |
| Sinh mã QR, in thẻ | thư viện `qrcode` (Python), xuất PDF |
| Lưu ảnh | thư mục trên máy (cấu hình được) |
| Đóng gói | Docker Compose |

Lý do chọn PostgreSQL: dữ liệu có nhiều quan hệ (tổ đội, công nhân, ca, chấm công, lượt kiểm tra); hỗ trợ tốt kiểu thời gian,
múi giờ và phép tính khoảng thời gian (tính công, ca qua đêm); có JSONB để lưu vùng kiểm tra; ràng buộc dữ liệu chặt
(mỗi công nhân chỉ một bản ghi công cho mỗi ca, kể cả khi hai lượt quét đến cùng lúc).

**Nguyên tắc kiến trúc:**
- **Backend là trung tâm.** Kiosk và web quản lý chỉ giao tiếp với backend, không gọi thẳng dịch vụ AI.
- **Dịch vụ AI chỉ "nhìn và trả lời":** không ghi cơ sở dữ liệu, không biết công nhân là ai, không quyết định ghi công.
  Backend gửi kèm vùng kiểm tra và danh sách đồ bảo hộ bắt buộc trong mỗi yêu cầu kiểm tra.
  Dịch vụ AI trả về kết quả + ảnh (JPEG); backend tự lưu ảnh và ghi dữ liệu.
- Dịch vụ AI đọc camera liên tục bằng **một luồng riêng tự viết** (`cv2.VideoCapture`), chỉ giữ khung hình mới nhất
  (tránh trễ do bộ đệm). **Chỉ chạy model khi có yêu cầu kiểm tra**; không dùng `model.predict(source=luồng camera)`
  chạy liên tục, vì trên CPU sẽ chiếm hết tài nguyên.
- Luồng hình xem trực tiếp cho kiosk/web: hiển thị khung hình gốc có vẽ **vùng kiểm tra**; khung nhận diện chỉ vẽ
  trong lúc đang kiểm tra (tiết kiệm CPU).
- Nguồn hình nhận được: file video (để chạy thử), webcam (số), URL RTSP/HTTP từ điện thoại.
  Đặt tên file kết quả không được dựa vào `Path(source).stem` khi nguồn là webcam hoặc URL.
- Kiosk không đăng nhập bằng tài khoản người dùng; mỗi kiosk được cấp **khóa riêng của cổng** để gửi lượt quét.
- Nếu dịch vụ AI không phản hồi: kiosk báo "Hệ thống kiểm tra tạm gián đoạn, vui lòng gặp cán bộ an toàn",
  cán bộ chấm công thủ công. Cổng không bao giờ bị kẹt.

## 9. Cơ sở dữ liệu (bản nháp)

- `users`: tài khoản đăng nhập, vai trò.
- `teams`: tổ đội, nhà thầu phụ.
- `workers`: mã, họ tên, ảnh, tổ đội, nghề, qr_token (UUID), trạng thái (đang làm/nghỉ/khóa).
- `gates`: cổng, địa chỉ camera, vùng kiểm tra (đa giác dạng JSON), cấu hình bảo hộ bắt buộc.
- `ppe_checks`: công nhân, cổng, thời gian, kết quả, thiếu gì, đường dẫn ảnh, độ tin cậy, trạng thái xác nhận.
- `shifts`: tên ca, giờ bắt đầu, giờ kết thúc, nghỉ giữa ca, ân hạn đi muộn, quét sớm tối đa, ca qua đêm, ca tăng ca.
- `shift_assignments`: ca, tổ đội HOẶC công nhân, từ ngày, đến ngày (phân theo cá nhân được ưu tiên hơn phân theo tổ).
- `attendance`: công nhân, ngày công, ca, giờ vào, giờ ra, ppe_check_id (lượt đạt cho phép vào ca),
  phút đi muộn, phút về sớm, số phút làm, trạng thái (bình thường/ngoài ca/thiếu giờ ra/chấm thủ công),
  lý do, người sửa, thời điểm sửa. Ràng buộc duy nhất: (công nhân, ngày công, ca).
- `settings`: thời hạn lưu ảnh, khung giờ hoạt động.

## 10. Các giai đoạn và tiêu chí hoàn thành

**Giai đoạn 0: Khảo sát code: ĐÃ XONG** (`docs/RA_SOAT.md`). Các quyết định rút ra ghi ở mục 12.

**Giai đoạn 1a: Dọn dẹp và chuẩn bị (làm trước, xong thì báo tôi)**
- Chuyển vào `_old/` các mục được xếp loại "CHUYỂN VÀO _old/" trong `docs/RA_SOAT.md` mục G
  (`run_tracking_demo.py`, `sanity_check.py`, `botsort_tracking_reid.yaml`, `zones.yaml`, `yolo11n.pt`, `yolo11m.pt`).
- Viết lại `README.md` theo hướng mới (ngắn: dự án là gì, cách cài, cách chạy chế độ cổng).
- Tạo **một file cấu hình chung** (ví dụ `configs/settings.yaml`): đường dẫn model, imgsz, conf, iou, vùng đầu/thân,
  các ngưỡng ở mục 5, thời gian kiểm tra, thư mục lưu ảnh. Code đọc tham số từ file này.
- Tra lớp theo tên (mục 4); sửa `test_compliance.py` cho phù hợp. **24 test cũ phải vẫn chạy OK.**
- Ghim phiên bản thư viện đang chạy được vào `requirements.txt` (kể cả torch).
- Kiểm tra máy có card NVIDIA không (`nvidia-smi`). Nếu có: **chỉ báo lại và đề xuất** cài torch bản CUDA, không tự cài.

**Giai đoạn 1b: Dịch vụ AI chế độ cổng**
- `evaluate_frames` và `check` theo mục 5 "Thuật toán kiểm tra". Viết test tự động cho `evaluate_frames`
  bằng dữ liệu giả (box giả), phủ đủ: DAT, KHONG_DAT thiếu mũ, thiếu áo, NHIEU_NGUOI, KHONG_CO_NGUOI,
  KHONG_XAC_DINH do ít khung hợp lệ, do đầu bị cắt, do tỷ lệ nằm giữa hai ngưỡng.
- Luồng đọc camera riêng, chỉ giữ khung mới nhất. **Chạy thử thật** với webcam và với điện thoại (app IP Webcam/DroidCam).
- Sửa `define_zone.py` để lưu tọa độ tỷ lệ 0–1; sửa `zone.py` quy đổi sang pixel lúc chạy (kèm test).
- Script chạy thử: đọc 1 file video hoặc camera, chạy `check`, in kết quả và lưu ảnh ra thư mục tạm.
- Hoàn thành khi: test tự động chạy OK, và chạy được trên video tôi tự quay với kết quả đúng với mắt thường
  ở các ca đủ đồ / thiếu mũ / thiếu áo / 2 người.

**Giai đoạn 2: Script đánh giá**
- Đầu vào: thư mục video ngắn, mỗi video 1 lượt (người đã đứng trong vùng kiểm tra), kèm file CSV đáp án
  (tên file, kết quả đúng, ghi chú điều kiện).
- **Mô phỏng tốc độ thật**: lấy mẫu khung theo FPS cấu hình (mặc định bằng FPS đo được trên máy), trong `timeout` giây
  tính từ đầu video, rồi gọi `evaluate_frames`.
- Đầu ra: độ chính xác, precision/recall cho "vi phạm", tỷ lệ không xác định, thời gian trung bình mỗi lượt,
  ma trận nhầm lẫn, và bảng lỗi theo từng điều kiện. Chạy với imgsz 640 và 960 để so sánh.
- Bộ video test phải có các trường hợp: đủ đồ; thiếu mũ; thiếu áo; thiếu cả hai; **mũ trắng**; mũ vàng/cam/xanh;
  **áo cam**, áo xanh lá, áo lưới; **nón lá, mũ lưỡi trai, mũ vải** (phải ra thiếu mũ); áo màu thường không phản quang
  (phải ra thiếu áo); 2 người cùng lúc; ngược sáng; thiếu sáng.

**Giai đoạn 3: Backend lõi**
Cơ sở dữ liệu, đăng nhập và phân quyền, API công nhân/tổ đội, sinh và in thẻ QR, API ca làm và phân ca,
API quét thẻ gọi dịch vụ AI, ghi chấm công và tính công theo mục "Ca làm", WebSocket.
**Bắt buộc viết test tự động cho phần tính công**: đi muộn trong/ngoài ân hạn, về sớm, ca qua đêm,
vào lại giữa ca, quét ngoài ca, thiếu giờ ra, hai ca trong một ngày, lượt không đạt rồi mới đạt.

**Giai đoạn 4: Trang kiosk**
Quét QR, các trạng thái màn hình (chờ / đang kiểm tra / đạt / không đạt / không xác định / lỗi thẻ), phát loa, tự quay về màn hình chờ.

**Giai đoạn 5: Web quản lý**
Trang tổng quan (tự cập nhật qua WebSocket), quản lý công nhân và tổ đội, in thẻ, quản lý ca và phân ca,
lịch sử lượt quét có ảnh và xác nhận đúng/báo nhầm, bảng công theo tháng và xuất Excel, chấm công thủ công,
cấu hình cổng và vẽ vùng kiểm tra.

**Giai đoạn 6: Phần mở rộng, Docker Compose, viết hướng dẫn chạy.**

## 11. Quy tắc làm việc cho trợ lý AI

1. **Làm từng giai đoạn một.** Xong mỗi bước: tóm tắt đã làm gì, chạy thử thế nào, kết quả ra sao, rồi chờ tôi xác nhận.
2. **Đọc code hiện có trước khi viết.** Ưu tiên sửa và tái sử dụng, không viết lại từ đầu những gì đã chạy được.
3. **Không tự ý** đổi model, đổi dataset, train lại, đổi công nghệ chính, hoặc thêm tính năng ngoài phạm vi. Muốn đổi thì đề xuất và giải thích lý do.
4. **Chạy thử code sau khi viết.** Không báo "xong" nếu chưa chạy được. Nếu không chạy được thì nói rõ lỗi gì.
5. Không xóa file cũ; nếu cần bỏ thì chuyển vào thư mục `_old/` và báo tôi.
6. Tham số (ngưỡng tin cậy, vùng đầu/thân, thời gian kiểm tra, đường dẫn) đặt trong file cấu hình, không hard-code.
7. Giải thích ngắn gọn bằng tiếng Việt. Tôi cần hiểu code để bảo vệ đồ án.
8. Không đưa API key, mật khẩu vào code; dùng file `.env`.
9. **Mọi test hiện có phải vẫn chạy OK** sau mỗi thay đổi. Đổi giao diện hàm thì sửa test tương ứng; code mới phải có test.
10. Khi `DE_TAI.md` mâu thuẫn với code hoặc với `docs/RA_SOAT.md`, dừng lại và hỏi tôi.

## 12. Nhật ký quyết định

**2026-10-17, sau rà soát (`docs/RA_SOAT.md` mục J):**
- J1: `ppe_monitor.py`, `clean_dataset.py` không có trong dự án. **Lấy `src/ppe/compliance.py` làm bản chính thức**,
  không viết lại hàm trùng chức năng.
- J2: **Giữ vùng đầu (-0.1, 0.35)** và các ngưỡng hiện tại, chỉ chuyển ra file cấu hình.
- J3: **Chế độ cổng không dùng tracking**; xét từng khung rồi bỏ phiếu (mục 5).
- J4: **Tọa độ vùng kiểm tra dạng tỷ lệ 0–1.**
- J5: **imgsz mặc định 640**, so sánh với 960 ở Giai đoạn 2 rồi chốt.
- J6: **Chuyển code hướng cũ vào `_old/` và viết lại README ngay đầu Giai đoạn 1** (Giai đoạn 1a).
- J7: **Commit `DE_TAI.md` và `docs/RA_SOAT.md` vào git.**

**2026-10-17, sau Giai đoạn 1b-1:**
- Chấp nhận các quyết định của trợ lý: tham số `detector` không bắt buộc trong `evaluate_frames` (để test dùng bộ phát hiện giả);
  làm sớm `zone_to_pixels`; thêm `missing_code`, `snapshot_jpeg_quality` vào cấu hình; thêm trường `dem_khung`, `ly_do`;
  gán đồ bảo hộ có xét cả người ngoài vùng.
- Mỗi khung mất khoảng 100 ms trên CPU. `check` phải **xử lý khung ngay khi lấy được**, không gom rồi mới xử lý.
- Chưa làm dừng sớm (trả kết quả trước khi hết `timeout` khi đã chắc chắn). Để sau, khi có số liệu Giai đoạn 2.
