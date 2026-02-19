# RockSat Video Acquisition Experiment
**University of Hartford | Spring 2026**

## Project Overview
This experiment is designed for the **NASA RockSat** program to capture high-definition flight footage during suborbital launch. The system utilizes a hardened Raspberry Pi setup to record 1080p video while adhering to strict range safety requirements regarding electromagnetic interference (EMI).

## Hardware Specifications
* **Controller:** Raspberry Pi Zero 2 W
* **Camera:** Raspberry Pi Camera Module 3
* **Interface:** USB Ethernet Gadget (Wired Control Only)
* **Storage:** High-speed microSD (formatted for raw MJPEG stream)

## System Constraints & Configuration
To comply with flight regulations, the following configurations are strictly enforced:
* **Transmission:** All wireless communication (Wi-Fi and Bluetooth) is disabled at the firmware level.
* **Connectivity:** System access is provided solely via a wired USB-C Ethernet Gadget connection.

## Software & Recording Pipeline
The acquisition script is written in **Python** and follows a three-stage process to ensure data integrity:

1. **Capture:** Records a 30-second 1080p30 MJPEG stream using `rpicam-vid`.
2. **Indexing:** Uses `ffmpeg` to remux the raw stream into a standard AVI container to rebuild the file index.
3. **Safe Termination:** Executes a controlled system shutdown to prevent SD card corruption during recovery.

### Execution
To run the acquisition script manually:
```bash
python3 capture_video.py
