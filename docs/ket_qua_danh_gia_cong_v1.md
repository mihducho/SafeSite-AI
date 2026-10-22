# Kết quả đánh giá kiểm tra bảo hộ tại cổng: bộ video `cong_gia_v1`

Đánh giá ngày 21/10/2026 (Giai đoạn 2 rút gọn, DE_TAI.md mục 10). Kết quả này đánh giá **toàn bộ luồng kiểm tra tại
cổng**, gồm model phát hiện và thuật toán bỏ phiếu theo nhiều khung, trên video tự quay. Kết quả của riêng model trên
tập test của dataset nằm ở [ket_qua_model_ppe.md](ket_qua_model_ppe.md).

## 1. Tóm tắt

- Với `imgsz` 640, hệ thống cho kết quả đúng **38/43 lượt (88.4%)**, và đúng **38/42 (90.5%)** khi bỏ lượt hệ thống
  chưa kết luận (`KHONG_XAC_DINH`).
- Phát hiện vi phạm: **precision 100%** (không người đủ đồ nào bị chặn nhầm), **recall 90.9%** (20/22 lượt vi phạm bị
  phát hiện). Chỉ 1 lượt vi phạm bị cho qua (ra `DAT`): người đội **nón lá**.
- Nhận đúng 100%: mũ bảo hộ trắng, áo phản quang cam và xanh, thiếu mũ, thiếu áo, thiếu cả hai, **mũ lưỡi trai** và
  **mũ bảo hiểm xe máy** (ra thiếu mũ), hai người đứng cạnh nhau, không có người.
- Chưa xử lý được: **hai người đứng trước–sau** (0/3) và **nón lá** (1/3).
- `imgsz` 960 cho kết quả kém hơn hẳn (12/43) và chậm gấp đôi. Đề xuất **chốt `imgsz` 640**.

## 2. Dữ liệu

43 video quay ngày 21/10/2026 bằng điện thoại đặt cố định, ở một địa điểm trong nhà, trong một buổi. Video quay dọc,
480×854 điểm ảnh, khoảng 29.8 khung/giây, dài 4.7–10.6 giây. Mỗi video là **một lượt kiểm tra**: người đã đứng
trong vùng kiểm tra từ đầu video. Đáp án được tạo từ tên file theo quy ước, rồi kiểm tra bằng tay
(`data/annotations/cong_gia_v1.csv`).

| Nhóm | Mô tả | Số video | Đáp án đúng |
|---|---|---|---|
| Đủ đồ | Mũ bảo hộ + áo phản quang | 4 | DAT |
| Mũ trắng | Mũ bảo hộ màu trắng + áo phản quang | 4 | DAT |
| Áo cam | Mũ bảo hộ + áo phản quang màu cam | 2 | DAT |
| Áo xanh | Mũ bảo hộ + áo phản quang màu xanh | 2 | DAT |
| Thiếu mũ | Không đội mũ, có áo | 4 | KHONG_DAT, thiếu mũ |
| Mũ lưỡi trai | Mũ lưỡi trai thay mũ bảo hộ, có áo | 4 | KHONG_DAT, thiếu mũ |
| Mũ bảo hiểm | Mũ bảo hiểm xe máy, có áo | 4 | KHONG_DAT, thiếu mũ |
| Nón lá | Nón lá, có áo | 3 | KHONG_DAT, thiếu mũ |
| Thiếu áo | Có mũ bảo hộ, không mặc áo phản quang | 4 | KHONG_DAT, thiếu áo |
| Thiếu cả hai | Không mũ, không áo | 3 | KHONG_DAT, thiếu mũ và áo |
| 2 người cạnh nhau | Hai người đứng cạnh nhau trong vùng | 3 | NHIEU_NGUOI |
| 2 người trước–sau | Một người đứng sau lưng người kia | 3 | NHIEU_NGUOI |
| Không có người | Vùng kiểm tra trống | 3 | KHONG_CO_NGUOI |
| **Tổng** | | **43** | 12 DAT, 22 KHONG_DAT, 6 NHIEU_NGUOI, 3 KHONG_CO_NGUOI |

## 3. Phương pháp

- **Model:** YOLO11s đã train (`weights/ppe_s`), ngưỡng tin cậy 0.35, IoU 0.7. Chỉ dùng 3 lớp: người, mũ bảo hộ,
  áo phản quang.
- **Vùng kiểm tra:** `cong_gia_v1`, vẽ trên video không có người, gần như phủ cả khung hình. Một người được tính là
  đứng trong vùng khi điểm giữa cạnh dưới khung nhận diện (điểm chân) nằm trong vùng.
- **Mô phỏng tốc độ chạy thật:** script đo tốc độ xử lý trên máy đánh giá (laptop Intel Core i5-1135G7, chỉ dùng
  CPU), được **11.7 khung/giây** với `imgsz` 640 và **4.1 khung/giây** với 960. Từ 1.5 giây đầu của mỗi video, script
  lấy khung theo đúng cách hệ thống thật làm: xử lý xong khung này thì lấy khung mới nhất. Kết quả là **18 khung**
  mỗi lượt với 640 và 7 khung với 960.
- **Thuật toán kiểm tra** (DE_TAI.md mục 5):
  - Mỗi khung được xếp vào một trong các loại: không có người, nhiều người, không hợp lệ (người quá nhỏ hoặc bị cắt
    đầu), hoặc hợp lệ. Với khung hợp lệ, mũ chỉ được tính khi nằm ở **vùng đầu**, áo chỉ được tính khi nằm ở
    **vùng thân** của người.
  - Bỏ phiếu: nếu ≥ 50% số khung có từ 2 người trở lên thì ra `NHIEU_NGUOI`. Nếu có ít hơn 3 khung hợp lệ thì ra
    `KHONG_CO_NGUOI` hoặc `KHONG_XAC_DINH`.
  - Ngược lại, tính tỷ lệ khung hợp lệ thấy từng món: ≥ 0.6 là có, ≤ 0.2 là thiếu, ở giữa là không chắc và ra
    `KHONG_XAC_DINH` (mời quét lại).
- **Cách tính chỉ số:**
  - Một lượt **đúng** khi kết quả trùng đáp án; với `KHONG_DAT` phải đúng cả danh sách thiếu.
  - **Precision/recall vi phạm** chỉ xét các lượt có đáp án DAT hoặc KHONG_DAT, với `KHONG_DAT` là dương tính.
    Lượt vi phạm mà hệ thống ra `KHONG_XAC_DINH` được tính là bỏ sót trong recall, dù về vận hành đây là trường hợp
    an toàn (người đó phải quét lại).

## 4. Kết quả (`imgsz` 640)

| Chỉ số | Giá trị |
|---|---|
| Tỷ lệ đúng | **38/43 (88.4%)** |
| Tỷ lệ đúng khi hệ thống đã kết luận | 38/42 (90.5%) |
| Tỷ lệ `KHONG_XAC_DINH` (mời quét lại) | 1/43 (2.3%) |
| Precision vi phạm | **100%** (20/20) |
| Recall vi phạm | **90.9%** (20/22) |
| Bỏ lọt (vi phạm nhưng ra DAT) | 1 (nón lá) |
| Chặn nhầm (đủ đồ nhưng ra KHONG_DAT) | 0 |

**Ma trận nhầm lẫn** (hàng: đáp án, cột: kết quả hệ thống):

| Đáp án \ Kết quả | DAT | KHONG_DAT | KHONG_XAC_DINH | NHIEU_NGUOI | KHONG_CO_NGUOI |
|---|---|---|---|---|---|
| DAT | **12** | 0 | 0 | 0 | 0 |
| KHONG_DAT | 1 | **20** | 1 | 0 | 0 |
| NHIEU_NGUOI | 0 | 3 | 0 | **3** | 0 |
| KHONG_CO_NGUOI | 0 | 0 | 0 | 0 | **3** |

**Theo nhóm:**

| Nhóm | Đúng | Kết quả hệ thống |
|---|---|---|
| Đủ đồ | 4/4 | DAT 4 |
| Mũ trắng | 4/4 | DAT 4 |
| Áo cam | 2/2 | DAT 2 |
| Áo xanh | 2/2 | DAT 2 |
| Thiếu mũ | 4/4 | KHONG_DAT 4 |
| Mũ lưỡi trai | 4/4 | KHONG_DAT 4 |
| Mũ bảo hiểm | 4/4 | KHONG_DAT 4 |
| Nón lá | 1/3 | DAT 1, KHONG_DAT 1, KHONG_XAC_DINH 1 |
| Thiếu áo | 4/4 | KHONG_DAT 4 |
| Thiếu cả hai | 3/3 | KHONG_DAT 3 |
| 2 người cạnh nhau | 3/3 | NHIEU_NGUOI 3 |
| 2 người trước–sau | 0/3 | KHONG_DAT 3 |
| Không có người | 3/3 | KHONG_CO_NGUOI 3 |

## 5. Phân tích các lượt sai

Nguyên nhân được xác định từ chi tiết từng khung mà script đánh giá ghi lại: các khung nhận diện, lớp, độ tin cậy.

### 5.1. Hai người đứng trước–sau (0/3)

Hệ thống ra `KHONG_DAT` (kiểm tra người đứng trước) thay vì `NHIEU_NGUOI`. Có hai nguyên nhân:

| Video | Khung model thấy 2 người | Khung được tính là 2 người |
|---|---|---|
| Trước–sau 01 | 0/18 | 0/18 |
| Trước–sau 02 | 3/18 | 3/18 |
| Trước–sau 03 | 12/18 | 6/18 |

1. **Người đứng sau bị che gần hết** nên model không phát hiện được (video 01, 02). Đây là giới hạn của một camera
   nhìn thẳng ngang người.
2. **Bước lọc khung trùng bỏ nhầm người đứng sau** (video 03). Bước này bỏ khung người nằm ≥ 80% bên trong một khung
   người lớn hơn, vì model hay vẽ 2 khung cho cùng một người. Khi người đứng sau gần như bị che, khung của họ nằm
   84–99% trong khung người phía trước nên bị bỏ. Nếu giữ lại, video 03 sẽ có 12/18 khung có 2 người (67%) và ra
   đúng `NHIEU_NGUOI`.

So sánh: với hai người **đứng cạnh nhau**, model thấy 2 người ở **100% số khung** (54/54) và kết quả đúng 3/3.

### 5.2. Nón lá (1/3)

Model **nhận nón lá là mũ bảo hộ** ở 23/54 khung, độ tin cậy trung vị 0.86, ngang mũ bảo hộ thật (0.87–0.91):

| Video | Khung bị tính là có mũ | Kết quả |
|---|---|---|
| Nón lá 01 | 18/18 | **DAT**, lượt bỏ lọt duy nhất |
| Nón lá 02 | 1/18 | KHONG_DAT (đúng) |
| Nón lá 03 | 4/18 (22%, nằm giữa 0.2 và 0.6) | KHONG_XAC_DINH: không kết luận, mời quét lại |

Đây là giới hạn của model. Dữ liệu train không có nón lá làm mẫu "không phải mũ bảo hộ", và nón lá cũng có dạng
vòm, vành rộng giống mũ bảo hộ.

### 5.3. Độ ổn định giữa các lần chạy

Chạy lại 3 lần với `imgsz` 640, mỗi lần đo lại tốc độ (11.0–12.0 khung/giây) nên khung được lấy mẫu hơi khác nhau.
**42/43 video cho cùng kết quả** cả 3 lần. Chỉ video nón lá 03 dao động giữa `KHONG_DAT` và `KHONG_XAC_DINH`, vì tỷ
lệ khung thấy "mũ" của video này nằm sát ngưỡng 0.2. Tỷ lệ đúng của 3 lần chạy là 38–39/43.

## 6. So sánh `imgsz` 640 và 960

| Chỉ số | 640 | 960 |
|---|---|---|
| Tỷ lệ đúng | **38/43 (88.4%)** | 12/43 (27.9%) |
| Recall vi phạm | **90.9%** | 22.7% |
| Thời gian xử lý 1 khung (trung vị, CPU) | **117 ms** | 230 ms |
| Số khung mỗi lượt (1.5 s) | 18 | 7 |

Với 960, model **tách một người thành hai khung**: một khung từ đầu tới hông, một khung từ vai tới chân. Hai khung
lệch nhau theo chiều dọc nên bước lọc khung trùng không bỏ được. Ở các video chỉ có một người, **190/238 khung**
(80%) bị tính là 2 người, và 27/34 video ra `NHIEU_NGUOI`. Nguyên nhân: model được train ở 640, trong khi tại cổng
người đứng gần và chiếm gần hết khung hình. Phóng ảnh lên 960 làm người trở nên to hơn nhiều so với dữ liệu train.

Kết luận: **chọn `imgsz` 640**. Kết quả tốt hơn hẳn và nhanh gấp khoảng 2 lần.

## 7. Nhận xét khác

- **Luật vùng đầu hoạt động đúng.** Trong cảnh có một chiếc mũ bảo hộ đặt cố định ở góc dưới bên phải. Model phát
  hiện chiếc mũ này ở mọi khung của video không có người, và ở 48 khung của các video không đội mũ bảo hộ. Tuy vậy,
  trong 270 khung của 4 nhóm không đội mũ bảo hộ (thiếu mũ, thiếu cả hai, mũ lưỡi trai, mũ bảo hiểm), **không khung
  nào** bị tính là người đó có mũ, vì chiếc mũ không nằm ở vùng đầu của người.
- **Mũ lưỡi trai và mũ bảo hiểm xe máy** không bị nhận là mũ bảo hộ ở khung nào trong bộ video này. Tuy vậy, trong
  lúc chạy thử trực tiếp bằng camera (20/10/2026), đã gặp trường hợp mũ lưỡi trai bị nhận là mũ bảo hộ (độ tin cậy
  0.56–0.82). Đây vẫn là rủi ro cần đo thêm.
- **Áo phản quang màu cam** được nhận với độ tin cậy thấp hơn rõ (trung vị 0.65, thấy ở 30/36 khung) so với áo
  vàng-xanh (0.89–0.91). Kết quả vẫn đúng 2/2 nhờ bỏ phiếu nhiều khung, nhưng khoảng an toàn hẹp hơn. Điều này khớp
  với nhận định trước đó rằng dữ liệu train ít áo cam.
- **Không có lượt chặn nhầm nào:** 12/12 lượt đủ đồ đều ra `DAT`.

## 8. Thời gian xử lý

- `imgsz` 640: **117 ms/khung** (trung vị; dao động 83–162 ms) trên CPU Intel Core i5-1135G7.
- Thời gian mỗi lượt trong mô phỏng là 2.1 giây (trung vị), cao hơn 1.5 giây. Lý do là tốc độ được đo một lần lúc
  bắt đầu (khoảng 85 ms/khung), còn máy chậm dần trong lúc chạy. Khi chạy thật, hệ thống luôn dừng đúng 1.5 giây và
  chỉ xử lý ít khung hơn, nên thời gian một lượt không vượt quá 1.5 giây cộng thời gian xử lý một khung.

## 9. Hạn chế

- **Bộ dữ liệu nhỏ:** 43 video, mỗi nhóm 2–4 video, một địa điểm trong nhà, một buổi, một vị trí đặt camera. Tỷ lệ
  theo từng nhóm chỉ mang tính tham khảo.
- **Chưa có các điều kiện DE_TAI yêu cầu:** ngược sáng, thiếu sáng, mũ vải, áo lưới, áo màu thường không phản
  quang, mũ bảo hộ các màu khác.
- Video được lấy mẫu theo tốc độ đo trên máy, chưa phải luồng camera trực tiếp. Độ phân giải 480×854 cũng thấp hơn
  camera dùng khi chạy thử trực tiếp (720×1280).
- Đáp án được tạo từ tên file và kiểm tra bằng tay.

## 10. Hướng tiếp theo

1. **Chốt `imgsz` 640** và ghi vào nhật ký quyết định (DE_TAI.md mục 12).
2. **Hai người đứng trước–sau:** thử đặt camera cao hơn, chúc xuống để thấy người phía sau, và xem lại bước lọc khung
   trùng. Cần cách phân biệt "khung trùng của cùng một người" với "người thứ hai bị che".
3. **Nón lá:** cân nhắc bổ sung ảnh nón lá, mũ lưỡi trai, mũ bảo hiểm làm mẫu "không phải mũ bảo hộ" rồi train
   tiếp. Việc này cần quyết định riêng vì thay đổi model.
4. **Mở rộng bộ video:** thêm các điều kiện còn thiếu ở mục 9, nhiều người và nhiều địa điểm hơn, rồi hiệu chỉnh các
   ngưỡng bỏ phiếu (đặc biệt là ngưỡng nhiều người 0.5).

## Phụ lục: chạy lại đánh giá

```
.venv\Scripts\python.exe scripts\make_answers.py --videos data\raw\cong_gia_v1 --answers data\annotations\cong_gia_v1.csv
.venv\Scripts\python.exe scripts\evaluate_videos.py --videos data\raw\cong_gia_v1 --answers data\annotations\cong_gia_v1.csv --gate cong_gia_v1 --imgsz 640
.venv\Scripts\python.exe scripts\evaluate_videos.py --videos data\raw\cong_gia_v1 --answers data\annotations\cong_gia_v1.csv --gate cong_gia_v1 --imgsz 960
```

Kết quả gốc của lần chạy dùng trong tài liệu này (không đưa lên git):

- 640: `runs/eval/20261021_224823_imgsz640/` (`tom_tat.md`, `ket_qua.csv`, `chi_tiet_khung.jsonl`, ảnh lượt sai trong `sai/`)
- 960: `runs/eval/20261021_225006_imgsz960/`
- Ảnh của mọi lượt (640): `runs/eval/20261021_232509_imgsz640/anh/`. Đây là lần chạy lại với cùng FPS (`--fps 11.7
  --save-images all`), kết quả trùng 43/43 video với lần chạy chính thức.
- Bộ file dùng cho báo cáo (bản sao các file trên, đáp án và 10 ảnh minh họa): `runs/eval/bao_cao_cong_gia_v1/`
