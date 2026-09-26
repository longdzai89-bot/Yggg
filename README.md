# Primitive Realm — Game Server + Godot Android Client

Bộ prototype hoàn chỉnh gồm admin panel, game backend WebSocket/HTTP, SQLite và client Godot 4. Kiến trúc được viết mới, chỉ tham khảo vòng lặp sinh tồn nguyên thủy; không sao chép code/UI/asset của game thương mại.

## 1. Chạy trên Termux

```bash
cp /sdcard/Download/game-server-tool.zip ~/
unzip -o ~/game-server-tool.zip -d ~/
cd ~/game-server-tool
bash scripts/run-termux.sh
```

Mặc định:
- Admin: `http://IP-LAN:3000`
- Game WebSocket: `ws://IP-LAN:7777/game`
- Admin mặc định: `admin / admin123`

Đổi secret/password trong `server-tool/.env` trước khi dùng ngoài LAN.

Lấy IP:
```bash
ip addr
ifconfig
curl ifconfig.me
```

## 2. Client

Godot 4 mở `game-client/project.godot`. Client có login/register, chọn IP server trong code prototype, di chuyển 4 hướng, combat request, enemy, inventory data và đồng bộ player qua WebSocket.

Để client Android kết nối máy khác, nhập LAN IP của máy chạy server và port `7777`. Không dùng `localhost` trừ khi server chạy cùng thiết bị.

## 3. GitHub Actions

```bash
git init
git branch -M main
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

Workflow `.github/workflows/build-apk.yml` dùng Godot headless + Android SDK và upload APK artifact. Godot command-line export hỗ trợ `--headless --export-release "Android" ...`; export Android cần export templates tương ứng với phiên bản Godot. Xem tài liệu Godot để thay phiên bản/template nếu runner thay đổi.

## 4. Assets

```bash
bash scripts/fetch-assets.sh
```

Script chỉ tải nguồn đã liệt kê trong `CREDITS.md`. Prototype hiện có graphics tự sinh trong GDScript để vẫn chạy ngay cả khi chưa tải asset ngoài.

## 5. Cấu trúc

```text
/server-tool       Flask + Jinja2 + Flask-Sock + SQLite
/game-client       Godot 4 Android client
/scripts            Termux/build/fetch scripts
/.github/workflows GitHub Actions
CREDITS.md
LICENSE-ASSETS.md
LICENSE
```

## 6. Lưu ý mạng

`7777` phải được mở trên firewall/router nếu thiết bị khác cần kết nối. Public IP không tự động có nghĩa là port 7777 đã được NAT/forward. Trong mạng di động/CGNAT, kết nối inbound từ Internet có thể không hoạt động; LAN là đường thử nghiệm đơn giản nhất.

## 7. Production hardening

Prototype này đủ để phát triển/chạy LAN, nhưng trước khi public Internet nên thêm HTTPS/WSS, rate limit, refresh-token/session rotation, validation packet, server-authoritative combat/inventory, reconnect/heartbeat, migration DB, backup retention, audit log và reverse proxy.
