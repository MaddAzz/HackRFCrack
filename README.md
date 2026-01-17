# HackRFCrack

**HackRFCrack** is a specialized tool designed to bring the functionality of [RFCrack](https://github.com/cclabsInc/RFCrack) to the **HackRF One**. While the original RFCrack relies on the CC1111 chip (Yard Stick One), this tool utilizes the HackRF's raw IQ capabilities to perform Replay Attacks, Jamming, and Signal Analysis.

## Features

*   **Replay Attack (`-i`)**: Capture a signal and immediately replay it. Ideal for testing RF-controlled devices.
*   **Jamming (`-j`)**: Transmit wideband noise on a specific frequency.
*   **Signal Analysis (`-a`)**: Demodulate OOK signals, visualize the waveform, and extract binary/hex data.
*   **Spy Bug Detector (`--salamandra`)**: Scan for hidden analog microphones.
*   **Drone Detector (`--drone`)**: Monitor airspace for UAV communication signals.
*   **Signal Decoder (`--rtl433`)**: Decode common ISM band devices (Weather stations, TPMS, etc.) using `rtl_433` integration.
*   **Web UI (`--webui`)**: A modern "Cyberpunk" style web interface to control the tool.

## Prerequisites

*   **Hardware**: HackRF One
*   **Software**:
    *   `hackrf` (host tools)
    *   `rtl_433` (for decoding support)
    *   Python 3
    *   `numpy`, `scipy`, `matplotlib`, `flask`

### Installation

```bash
# Install system tools
sudo apt update
sudo apt install hackrf rtl-433

# Install Python dependencies
pip3 install numpy scipy matplotlib flask
```

## Usage

### CLI Mode

```bash
python3 HackRFCrack.py [OPTIONS]
```

**Examples:**
```bash
# Replay Attack on 315 MHz
python3 HackRFCrack.py -i -F 315000000

# Jam 433 MHz
python3 HackRFCrack.py -j -F 433000000

# Scan for Spy Bugs
python3 HackRFCrack.py --salamandra

# Detect Drones
python3 HackRFCrack.py --drone

# Decode Signals using rtl_433
python3 HackRFCrack.py --rtl433 -F 433920000
```

### Web UI Mode

Launch the web interface:

```bash
python3 HackRFCrack.py --webui
```
Then open your browser at **http://localhost:5000**.

## Options

| Flag | Description | Default |
| :--- | :--- | :--- |
| `-i`, `--instant_replay` | Record and Replay Signal | |
| `-j`, `--jammer` | Jam a frequency | |
| `-a FILE` | Analyze capture file | |
| `--salamandra` | Launch Salamandra Spy Bug Detector | |
| `--drone` | Launch Drone Detector | |
| `--rtl433` | Launch rtl_433 Decoder | |
| `--webui` | Launch Web Interface | |
| `-F FREQ` | Frequency in Hz | `315000000` |
| `-S RATE` | Sample Rate | `2000000` |

## Disclaimer
This tool is for educational and authorized testing purposes only. Users are responsible for complying with local radio frequency regulations.