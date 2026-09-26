#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../game-client"
command -v godot >/dev/null || { echo 'Godot not found'; exit 1; }
godot --headless --path . --export-release "Android" ../builds/PrimitiveRealm.apk
