#!/data/data/com.termux/files/usr/bin/bash
set -e
ZIP=${1:-/sdcard/Download/game-server-tool.zip}
cd ~
unzip -o "$ZIP"
cd game-server-tool
chmod +x scripts/*.sh
echo "Ready: cd ~/game-server-tool && bash scripts/run-termux.sh"
