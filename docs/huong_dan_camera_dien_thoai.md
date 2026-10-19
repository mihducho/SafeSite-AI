# Hướng dẫn dùng điện thoại làm camera cổng (Giai đoạn 1b-2)

Mục tiêu: điện thoại phát hình qua Wi-Fi, laptop đọc bằng một URL, rồi chạy thử kiểm tra tại cổng
(`scripts/run_checkpoint.py`) và gửi kết quả lại. Chọn **một** trong hai app: IP Webcam (chỉ Android, dễ chỉnh
độ phân giải) hoặc DroidCam (Android và iPhone).

## 1. Chuẩn bị mạng

- Điện thoại và laptop phải **cùng một mạng Wi-Fi**. Không dùng Wi-Fi "khách" ở quán cà phê, công ty: các mạng này
  thường chặn các máy nhìn thấy nhau.
- Không có Wi-Fi chung thì bật **điểm phát sóng (hotspot)** trên điện thoại rồi cho laptop kết nối vào. App sẽ hiện
  đúng địa chỉ IP để dùng.
- Cắm sạc cho điện thoại, vì phát hình liên tục rất tốn pin.

## 2a. Cách 1: app IP Webcam (Android)

1. Cài **IP Webcam** (tác giả Pavel Khlebovich) từ Google Play.
2. Mở app, vào **Video preferences**:
   - **Video resolution**: chọn **1280x720** (khớp với webcam laptop, CPU xử lý vừa sức).
   - **Quality**: khoảng 50–70 (thấp hơn thì mượt hơn).
3. Kéo xuống cuối, bấm **Start server**. Màn hình hiện địa chỉ dạng `http://192.168.1.23:8080`. Ghi lại địa chỉ này.
4. Trên laptop, mở trình duyệt vào đúng địa chỉ đó (ví dụ `http://192.168.1.23:8080`). Thấy trang của IP Webcam và
   hình camera là kết nối được.
5. **URL dùng cho dự án**: thêm `/video` vào cuối, ví dụ **`http://192.168.1.23:8080/video`**.

> Nếu bạn đặt tên đăng nhập/mật khẩu trong app, URL có dạng `http://ten:matkhau@192.168.1.23:8080/video`.
> Chỉ gõ URL này trên dòng lệnh, **không ghi vào file cấu hình hay đưa lên git** (quy tắc 11.8 trong `DE_TAI.md`).

## 2b. Cách 2: app DroidCam (Android hoặc iPhone)

1. Cài **DroidCam** (Dev47Apps) trên điện thoại. Laptop **không cần** cài phần mềm DroidCam Client.
2. Mở app. Màn hình hiện **WiFi IP** (ví dụ `192.168.1.23`) và **DroidCam Port** (thường là `4747`).
3. Trên laptop, mở trình duyệt vào `http://192.168.1.23:4747/video`. Thấy hình là được, rồi **đóng tab trình duyệt
   đó lại**, vì DroidCam thường chỉ cho một nơi xem cùng lúc.
4. **URL dùng cho dự án**: **`http://192.168.1.23:4747/video`**.

> Bản miễn phí của DroidCam có thể giới hạn độ phân giải thấp (khoảng 640x480). Script sẽ in ra độ phân giải thật
> nhận được, bạn ghi lại khi gửi kết quả.

## 3. Đặt điện thoại

- Đặt cao khoảng **1.6–2 m**, hơi chúc xuống. Người đứng cách **3–4 m** phải thấy **toàn thân, cả bàn chân**, và
  đầu cách mép trên khung hình một khoảng. Nếu đầu chạm mép trên, hệ thống coi khung đó không hợp lệ (đầu bị cắt).
- **Đặt dọc hay ngang đều được.** Một số app (như DroidCam) vẫn phát hình **ngang** khi điện thoại dựng **dọc**,
  làm người trong hình bị **nằm ngang**. Khi đó thêm `--rotate 90` (xoay 90° theo chiều kim đồng hồ) lúc vẽ vùng
  ở bước 4.2. Góc xoay được lưu cùng vùng của cổng, nên các lệnh có `--gate` tự xoay theo. Nếu hình bị lộn ngược
  thì dùng `--rotate 270`. Lệnh thử ở bước 4.1 (chưa có `--gate`) cũng cần thêm `--rotate 90`.
- Tránh để camera nhìn thẳng ra cửa sổ sáng (ngược sáng).
- Giữ app chạy ở màn hình chính, không khóa màn hình: một số máy tự tắt camera khi tắt màn hình.

## 4. Chạy thử

Mở terminal trong VS Code ở thư mục dự án. Thay `URL` bằng địa chỉ ở bước 2, ví dụ
`http://192.168.1.23:8080/video`.

**4.1. Kiểm tra laptop đọc được hình** (chưa cần vùng kiểm tra):
```
.venv\Scripts\python.exe scripts\run_checkpoint.py --source URL --rounds 3
```
Dòng `Nguon: url ... | khung 1280x720` là đọc được. Báo lỗi `Khong mo duoc nguon hinh` thì xem mục 5.

**4.2. Vẽ vùng kiểm tra cho cổng** (vùng sàn nơi công nhân đứng, vì hệ thống xét **điểm chân** của người):
```
.venv\Scripts\python.exe scripts\define_zone.py --source URL --gate cong_1
```
Click chuột các góc của vùng sàn (ít nhất 3 điểm), bấm `s` để lưu. Vùng được lưu dạng tỷ lệ 0–1 vào
`configs/gates.yaml`.

**4.3. Chạy kiểm tra cho từng trường hợp.** Một người đứng trong vùng, nhìn về camera, đứng yên khi lệnh đang chạy.
Mỗi trường hợp chạy 3 lượt:
```
.venv\Scripts\python.exe scripts\run_checkpoint.py --source URL --gate cong_1 --rounds 3 --pause 3
```

| Lần chạy | Tình huống | Kết quả mong đợi |
|---|---|---|
| 1 | Đội mũ bảo hộ + mặc áo phản quang | `DAT` |
| 2 | Không đội mũ, có áo | `KHONG_DAT` thiếu `thieu_mu` |
| 3 | Có mũ, không mặc áo | `KHONG_DAT` thiếu `thieu_ao` |
| 4 | Hai người cùng đứng trong vùng | `NHIEU_NGUOI` |
| 5 | Không ai trong vùng | `KHONG_CO_NGUOI` |

Chưa có mũ hoặc áo bảo hộ thì cứ chạy các trường hợp làm được, ghi chú lại trường hợp nào chưa làm.

## 5. Xử lý lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `Khong mo duoc nguon hinh` hoặc `Khong nhan duoc khung hinh nao` | Kiểm tra lại URL (có `/video` ở cuối), app còn chạy, hai máy cùng mạng Wi-Fi. Mở thử URL trong trình duyệt |
| DroidCam: trình duyệt xem được nhưng script không đọc được | Đóng tab trình duyệt đang xem DroidCam rồi chạy lại |
| Hình giật, ít khung mỗi lượt | Giảm độ phân giải hoặc Quality trong app, để điện thoại gần bộ phát Wi-Fi |
| Đang chạy thì mất hình | Chương trình tự kết nối lại sau 2 giây (`camera.reconnect_delay_s`). Mất hẳn thì lượt đó báo lỗi camera |
| Luôn ra `KHONG_XAC_DINH` | Xem `dem_khung` trong kết quả. Nhiều `qua_nho` thì đứng gần hơn hoặc tăng độ phân giải. Nhiều `cat_dau` thì hạ góc camera để thấy cả đầu |
| Người trong ảnh kết quả bị nằm ngang | Điện thoại dựng dọc nhưng app phát hình ngang: vẽ lại vùng với `--rotate 90` (mục 3) |
| `Loi: cong '...': vung da ve tren hinh xoay ...` | Đã gõ `--rotate` khác với góc đã lưu cùng vùng. Bỏ `--rotate` đi, hoặc vẽ lại vùng với góc mới |

## 6. Gửi lại cho trợ lý

1. **Toàn bộ chữ in ra trong terminal** của các lần chạy ở bước 4: copy rồi dán.
2. App đã dùng (IP Webcam hay DroidCam), độ phân giải đã chọn trong app.
3. Các file `.json` trong `runs\checkpoint\` (ghi kết quả từng lượt, không chứa ảnh). Phần `chi_tiet_khung` ghi
   từng khung trên 1 dòng: các box model thấy (lớp, độ tin cậy, tọa độ tỷ lệ 0–1), loại khung, người được tính trong
   vùng. Nhờ đó trợ lý tìm được nguyên nhân kết quả sai mà không cần xem ảnh.
4. Ảnh `.jpg` trong cùng thư mục **chỉ khi bạn muốn**. Ảnh có chụp người, bạn tự quyết có gửi hay không.
