#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1 || ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "Reel Studio needs Python 3.10+ and FFmpeg. See README.md for setup."
  read -r answer
  exit 1
fi
python3 launcher.py
