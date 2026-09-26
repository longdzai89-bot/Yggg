#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")/.."
pkg update -y >/dev/null 2>&1 || true
pkg install python git unzip curl -y
cd server-tool
python -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
# launch admin and game WebSocket listeners; both use same Flask app/routes.
python run.py > ../server-admin.log 2>&1 & echo $! > ../admin.pid
SERVER_ROLE=game python run.py > ../server-game.log 2>&1 & echo $! > ../game.pid
sleep 2
LAN_IP=$(python - <<'PY'
import socket
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
try:s.connect(('8.8.8.8',80));print(s.getsockname()[0])
except:print('127.0.0.1')
s.close()
PY
)
PUBLIC_IP=$(curl -fsS --max-time 4 https://api.ipify.org || echo unavailable)
ADMIN_USER=$(grep '^ADMIN_USER=' .env | cut -d= -f2-); ADMIN_PASS=$(grep '^ADMIN_PASS=' .env | cut -d= -f2-)
echo ""
echo "🌐 Admin Panel : http://$LAN_IP:3000"
echo "🎮 Game Server : $LAN_IP:7777"
echo "🌍 Public IP   : $PUBLIC_IP"
echo "👤 Admin       : $ADMIN_USER / $ADMIN_PASS"
echo ""
echo "Logs: server-admin.log | server-game.log"
wait
