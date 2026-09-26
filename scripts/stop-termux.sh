#!/data/data/com.termux/files/usr/bin/bash
for f in admin.pid game.pid; do [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null || true; done
echo stopped
