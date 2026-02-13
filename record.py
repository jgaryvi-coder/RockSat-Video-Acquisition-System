#!/usr/bin/env python3
"""
record.py — Pi Zero 2 W + Camera Module 3
MJPEG 1080p30 for 30 seconds, remux to rebuild AVI index, optional shutdown.
"""

from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# ---- Settings ----
FPS = 30
WIDTH = 1920
HEIGHT = 1080
QUALITY = 60
DURATION_MS = 30000
OUTDIR = Path.home() / "videos"
SHUTDOWN_AT_END = True  # set False while testing over SSH
MIN_FREE_GB = 1.0       # Safety check for MJPEG files

def run(cmd: list[str], ignore_fail: bool = False) -> None:
    """Wrapper for subprocess with logging."""
    print(f"\n$ {' '.join(cmd)}", flush=True)
    try:
        subprocess.run(cmd, check=not ignore_fail)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        if not ignore_fail:
            raise

def check_disk_space(path: Path):
    """Ensure there is enough room for MJPEG data."""
    _, _, free = shutil.disk_usage(path.anchor)
    free_gb = free / (2**30)
    if free_gb < MIN_FREE_GB:
        print(f"Error: Low disk space ({free_gb:.2f} GB). Need at least {MIN_FREE_GB} GB.")
        exit(1)

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
        ])

        run(["sync"])

        # --- Remux to rebuild index ---
        print("Remuxing to rebuild AVI index...")
        try:
            # -y: overwrite, -stats: show progress
            run(["ffmpeg", "-y", "-v", "warning", "-stats", "-i", str(raw), "-c", "copy", str(fixed)])
        except subprocess.CalledProcessError:
            print("Copy remux failed; falling back to MJPEG re-encode...")
            run(["ffmpeg", "-y", "-v", "warning", "-i", str(raw), "-r", str(FPS), "-c:v", "mjpeg", "-q:v", "2", str(fixed)])

    finally:
        # --- Cleanup ---
        # We use finally to ensure temp files are deleted even if FFmpeg fails
        for temp_file in [raw, pts]:
            if temp_file.exists():
                print(f"Cleaning up {temp_file.name}...")
                temp_file.unlink()

        run(["sync"])

    print(f"Done. Saved clean file: {fixed}")

    if SHUTDOWN_AT_END:
        print("All done — shutting down safely...")
        run(["sudo", "shutdown", "-h", "now"])

    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user. Cleaning up and syncing...")
        run(["sync"], ignore_fail=True)
        # We don't shutdown on manual interrupt to allow user to check what happened
        sys.exit(1)
