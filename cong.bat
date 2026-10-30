@echo off
rem Mo MAN HINH CONG tren Microsoft Edge o che do kiosk (toan man hinh), LOA LUON BAT: tham so
rem --autoplay-policy=no-user-gesture-required cho phep phat giong doc / tieng bip ma khong can bam vao trang.
rem Dung ho so Edge rieng (data\edge_cong) de tham so co tac dung ca khi Edge khac dang mo; lan dau phai dang nhap.
rem Chay sau khi da bat ung dung (.\web). Thoat che do kiosk: Alt+F4.
cd /d "%~dp0"
start "" msedge --kiosk "http://127.0.0.1:8000/man-hinh-cong" --edge-kiosk-type=fullscreen --no-first-run ^
  --autoplay-policy=no-user-gesture-required --user-data-dir="%~dp0data\edge_cong"
