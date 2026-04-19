#!/usr/bin/env python3
from __future__ import annotations
"""
record.py — Pi Zero 2 W + Camera Module 3
RockSat Flight Script: Includes countdown, run-counter (RTC fix), and persistent logging.
"""

import os
import sys
import shutil
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime

# ---- Settings ----
FPS = 30
WIDTH = 1920
HEIGHT = 1080
QUALITY = 60
REC_DURATION_MS = 320000    # Recording length in milliseconds (e.g., 30000 = 30 seconds)
START_DELAY_SEC = 120       # Countdown delay in seconds before recording starts
SHUTDOWN_AT_END = False    # Set to True to turn off the Pi automatically after running

OUTDIR = Path.home() / "Desktop/Videos"
MIN_FREE_GB = 1.0          # Safety check to prevent SD card corruption
LOG_FILE = OUTDIR / "flight_log.txt"

# Ensure output directory exists before configuring logging
OUTDIR.mkdir(parents=True, exist_ok=True)

# ---- Logging Setup ----
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
# Also print to the console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)

def run(cmd: list[str], ignore_fail: bool = False) -> bool:
    """Helper function to execute system commands and log the output."""
    cmd_str = ' '.join(cmd)
    logging.info(f"Executing: {cmd_str}")
    try:
        subprocess.run(cmd, check=not ignore_fail, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed (ignored={ignore_fail}): {cmd_str}\nError: {e.stderr}"
        if ignore_fail:
            logging.warning(error_msg)
            return False
        else:
            logging.error(error_msg)
            raise

def check_disk_space(path: Path):
    """Ensures there is enough room on the SD card before starting."""
    _, _, free = shutil.disk_usage(path.anchor)
    free_gb = free / (2**30)
    if free_gb < MIN_FREE_GB:
        logging.error(f"Low disk space ({free_gb:.2f} GB). Aborting.")
        sys.exit(1)

def get_unique_basename(outdir: Path, ts: str) -> str:
    """
    Prevents overwriting files if the Pi lacks an RTC and reboots to 1970-01-01.
    Finds the next available run number.
    """
    counter = 1
    while True:
        name = f"flight_cam_{ts}_run{counter:03d}"
        if not (outdir / f"{name}_raw.avi").exists() and not (outdir / f"{name}.avi").exists():
            return name
        counter += 1

def main() -> int:
    logging.info("=== INITIALIZING FLIGHT CAMERA SCRIPT ===")
    check_disk_space(OUTDIR)

    # Start Countdown
    if START_DELAY_SEC > 0:
        logging.info(f"Waiting {START_DELAY_SEC} seconds before recording...")
        time.sleep(START_DELAY_SEC)

    # Generate Filenames
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name_base = get_unique_basename(OUTDIR, ts)

    raw = OUTDIR / f"{name_base}_raw.avi" # The actual data captured
    fixed = OUTDIR / f"{name_base}.avi"   # The playable version after remuxing
    pts = OUTDIR / f"{name_base}.pts"     # Presentation Time Stamps for recovery

    logging.info(f"Recording for {REC_DURATION_MS/1000}s. Outputting to: {raw}")

    try:
        # Capture Video
        run([
            "rpicam-vid", "-n",
            "--codec", "mjpeg",
            "--quality", str(QUALITY),
            "--width", str(WIDTH),
            "--height", str(HEIGHT),
            "--framerate", str(FPS),
            "-t", str(REC_DURATION_MS),
            "--save-pts", str(pts),
            "-o", str(raw),
        ], ignore_fail=True)

        # Force write to SD card
        logging.info("Syncing raw video to SD card...")
        run(["sync"])
        time.sleep(1)

        # Remuxing to rebuild AVI index
        if raw.exists() and raw.stat().st_size > 0:
            logging.info("Remuxing to rebuild AVI index...")
            try:
                run(["ffmpeg", "-y", "-v", "warning", "-stats", "-i", str(raw), "-c", "copy", str(fixed)])
            except subprocess.CalledProcessError:
                logging.warning("Copy remux failed; falling back to re-encode...")
                run(["ffmpeg", "-y", "-v", "warning", "-i", str(raw), "-r", str(FPS), "-c:v", "mjpeg", "-q:v", "2", str(fixed)])
        else:
            logging.error(f"Raw file {raw} was not created or is empty.")
            return 1

    finally:
        # Final sync to protect the SD card data before power-off
        logging.info("Final data sync...")
        run(["sync"])

    logging.info("Script completed successfully.")
    logging.info(f"Files kept in {OUTDIR}: {raw.name} & {fixed.name}")

    # Automatic Shutdown
    if SHUTDOWN_AT_END:
        logging.info("Initiating safe shutdown...")
        run(["sudo", "shutdown", "-h", "now"])

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logging.warning("Interrupted by user (Ctrl+C). Syncing...")
        run(["sync"], ignore_fail=True)
        sys.exit(1)
    except Exception as e:
        logging.critical(f"Unhandled exception: {e}")
        run(["sync"], ignore_fail=True)
        sys.exit(1)
