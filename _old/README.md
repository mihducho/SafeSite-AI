# _old/: file của hướng cũ (không dùng nữa)

Đợt 1 chuyển vào đây ở Giai đoạn 1a (2026-10-17), theo `docs/RA_SOAT.md` mục G và `DE_TAI.md` mục 10, 12.
Đợt 2 (2026-10-29, dọn code sau F3) gồm phần còn lại của hướng giám sát công trường bằng tracking.
Không xóa để còn tham khảo khi viết luận văn (phần "Vì sao đổi hướng"). Các script ở đây **không còn chạy được**
nếu không sửa đường dẫn import, vì đã rời khỏi `scripts/`, `src/`, `tests/`.

| File | Lý do |
|---|---|
| `scripts/run_tracking_demo.py` | Demo Phase 1 hướng cũ (model COCO, lọc người nhầm xe máy) |
| `scripts/sanity_check.py` | Kiểm tra cài đặt bằng model COCO |
| `configs/botsort_tracking_reid.yaml` | `PersonTracker` không hỗ trợ ReID; thí nghiệm ReID không cải thiện |
| `configs/zones.yaml` | Vùng cấm (tọa độ pixel) của các video công trường thử nghiệm |
| `yolo11n.pt`, `yolo11m.pt` | Model COCO chỉ dùng cho demo và thí nghiệm hướng cũ (không nằm trong git) |
| `scripts/run_safety_demo.py` | Đợt 2. Demo giám sát công trường (detect + track từng khung, vùng nguy hiểm); chế độ cổng không tracking |
| `src/tracking/`, `tests/test_tracker.py` | Đợt 2. `PersonTracker` (BoT-SORT) và test của nó, chỉ `run_safety_demo.py` dùng; bỏ luôn gói `lap` khỏi `requirements.txt` |
| `configs/botsort_tracking.yaml` | Đợt 2. Cấu hình BoT-SORT của `PersonTracker` (bỏ khoá `paths.tracker_config` trong `settings.yaml`) |
| `scripts/extract_frames.py` | Đợt 2. Cắt khung video để tự gán nhãn; model PPE cuối cùng train trên dataset Roboflow nên không dùng |
| `yolo11s.pt` | Đợt 2. Model gốc COCO để train lại (không nằm trong git); `train.py` trên Colab tự tải nếu thiếu |

Cũng ở đợt 2, hai hàm không còn ai gọi đã được bỏ khỏi code (xem lại bằng `git show 68f520e:<file>`):
`make_class_overlap_filter` trong `src/utils/postprocess.py` (chỉ `run_tracking_demo.py` dùng) và `detect()` trong
`src/detection/detect.py` (chỉ `run_safety_demo.py` dùng); khoá `paths.snapshot_dir` (đã ghi "[cu]", không code nào đọc).
