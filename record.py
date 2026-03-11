#!/usr/bin/env python3
from __future__ import annotations
"""
record.py — Pi Zero 2 W + Camera Module 3
MJPEG 1080p30 for 30 seconds.
Redundant saving: keeps BOTH the raw capture and the remuxed index.
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime

# ---- Settings ----
FPS = 30
WIDTH = 1920
HEIGHT = 1080
QUALITY = 60
DURATION_MS = 30000
OUTDIR = Path.home() / "videos"
SHUTDOWN_AT_END = False  # Set to True for deployment
MIN_FREE_GB = 1.0        # Safety check

def run(cmd: list[str], ignore_fail: bool = False) -> bool:
    print(f"\n$ {' '.join(cmd)}", flush=True)
    try:
        subprocess.run(cmd, check=not ignore_fail)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Command returned error (ignored={ignore_fail}): {e}")
        if not ignore_fail:
            raise
        return False

def check_disk_space(path: Path):
    _, _, free = shutil.disk_usage(path.anchor)
    free_gb = free / (2**30)
    if free_gb < MIN_FREE_GB:
        print(f"Error: Low disk space ({free_gb:.2f} GB).")
        sys.exit(1)

def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    check_disk_space(OUTDIR)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name_base = f"mjpeg_{WIDTH}x{HEIGHT}_{FPS}fps_{ts}"

    raw = OUTDIR / f"{name_base}_raw.avi"
    fixed = OUTDIR / f"{name_base}.avi"
    pts = OUTDIR / f"{name_base}.pts"

    print(f"Recording for {DURATION_MS/1000}s to: {raw}")

    try:
        # --- Record ---
        # ignore_fail=True handles the SIGABRT crash while saving data
        run([
            "rpicam-vid", "-n",
            "--codec", "mjpeg",
            "--quality", str(QUALITY),
            "--width", str(WIDTH),
            "--height", str(HEIGHT),
            "--framerate", str(FPS),
            "-t", str(DURATION_MS),
            "--save-pts", str(pts),
            "-o", str(raw),
        ], ignore_fail=True)

        # Force write to SD card immediately
        run(["sync"])
        time.sleep(1)

        # --- Remux ---
        if raw.exists() and raw.stat().st_size > 0:
            print("Remuxing to rebuild AVI index...")
            try:
                run(["ffmpeg", "-y", "-v", "warning", "-stats", "-i", str(raw), "-c", "copy", str(fixed)])
            except subprocess.CalledProcessError:
                print("Copy remux failed; falling back to re-encode...")
                run(["ffmpeg", "-y", "-v", "warning", "-i", str(raw), "-r", str(FPS), "-c:v", "mjpeg", "-q:v", "2", str(fixed)])
        else:
            print(f"Error: Raw file {raw} was not created.")
            return 1

    finally:
        # --- CLEANUP REMOVED ---
        # We no longer unlink/delete raw or pts files.
        # This ensures maximum data recovery if power is lost.
        run(["sync"])

    print(f"Done. Files kept in {OUTDIR}:")
    print(f"  1. {raw.name} (Original Data)")
    print(f"  2. {fixed.name} (Fixed/Index rebuilt)")

    if SHUTDOWN_AT_END:
        print("All done — shutting down safely...")
        run(["sudo", "shutdown", "-h", "now"])

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted. Syncing...")
        run(["sync"], ignore_fail=True)
        sys.exit(1)
