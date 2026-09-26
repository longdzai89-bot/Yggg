#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; OUT="$ROOT/game-client/assets/external"; mkdir -p "$OUT"
fetch(){ url="$1"; name="$2"; echo "Downloading $name"; curl -L --fail --retry 2 -o "$OUT/$name" "$url"; }
# Verified CC0 direct file from OpenGameArt.
fetch "https://opengameart.org/sites/default/files/npc.png" "cavemen_sprite_sheet_cd_mir_cc0.png"
# CC0 Stone Age set page is retained in CREDITS; its filename contains spaces and may be unavailable to some curl mirrors.
# If the direct file is reachable, uncomment:
# fetch "https://opengameart.org/sites/default/files/stone%20age%20sprites.png" "stone_age_sprites_vwolfdog_cc0.png"
echo "Assets saved to $OUT"
