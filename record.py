#!/usr/bin/env python3
"""
record.py — Pi Zero 2 W + Camera Module 3
MJPEG 1080p30 for 30 seconds, remux to rebuild AVI index, optional shutdown.
"""

from __future__ import annotations
import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# ---- Settings ----
FPS = 30
WIDTH = 1920
HEIGHT = 1080
QUALITY = 60
DURATION_MS = 30000  # 30 seconds
OUTDIR = Path.home() / "videos"
SHUTDOWN_AT_END = True  # set False while testing over SSH

def run(cmd: list[str]) -> None:
    print("\n$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)

def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_at_%Hh%Mm%Ss")
    raw = OUTDIR / f"mjpeg_{WIDTH}x{HEIGHT}_{FPS}fps_{ts}_raw.avi"
    fixed = OUTDIR / f"mjpeg_{WIDTH}x{HEIGHT}_{FPS}fps_{ts}.avi"
    pts = raw.with_suffix("").as_posix() + ".pts"  # like "${RAW%.avi}.pts"

    print(f"Recording raw video to: {raw}")

    # --- Record ---
    run([
        "rpicam-vid", "-n",
        "--codec", "mjpeg",
        "--quality", str(QUALITY),
        "--width", str(WIDTH),
        "--height", str(HEIGHT),
        "--framerate", str(FPS),
        "-t", str(DURATION_MS),
        "--save-pts", pts,
        "-o", str(raw),
    ])

    run(["sync"])

    # --- Remux to rebuild index ---
    print("Remuxing to rebuild AVI index...")
    try:
        # Fast path: no re-encode
        run(["ffmpeg", "-v", "error", "-i", str(raw), "-c", "copy", str(fixed)])
    except subprocess.CalledProcessError:
        # Fallback: re-encode MJPEG at correct FPS (still avoids input format guessing issues)
        print("Copy remux failed; falling back to MJPEG re-encode...")
        run(["ffmpeg", "-v", "error", "-i", str(raw), "-r", str(FPS), "-c:v", "mjpeg", "-q:v", "2", str(fixed)])

    # --- Cleanup ---
    if raw.exists():
        raw.unlink(missing_ok=True)
    run(["sync"])

    print(f"Done. Saved clean file: {fixed}")

    if SHUTDOWN_AT_END:
        print("All done — shutting down safely...")
        run(["sudo", "sync"])
        run(["sudo", "shutdown", "-h", "now"])
    else:
        print("SHUTDOWN_AT_END=False (not shutting down).")

    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted. Syncing...")
        subprocess.run(["sync"])
        raise
