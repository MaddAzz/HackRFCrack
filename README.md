# HackRFCrack

**HackRFCrack** is a specialized tool designed to bring the functionality of [RFCrack](https://github.com/cclabsInc/RFCrack) to the **HackRF One**. While the original RFCrack relies on the CC1111 chip (Yard Stick One), this tool utilizes the HackRF's raw IQ capabilities to perform Replay Attacks, Jamming, and Signal Analysis.

## Features

*   **Replay Attack (`-i`)**: Capture a signal and immediately replay it. Ideal for testing RF-controlled devices like doorbells, gates, and simple remotes.
*   **Jamming (`-j`)**: Transmit wideband noise on a specific frequency to block communications.
*   **Signal Analysis (`-a`)**: Analyze captured IQ data to demodulate OOK (On-Off Keying) signals, visualize the waveform, and extract binary/hex data.
    *   *Includes automatic graph generation!*

## Prerequisites

*   **Hardware**: HackRF One
*   **Software**:
    *   `hackrf` (host tools: `hackrf_transfer`, `hackrf_info`)
    *   Python 3
    *   `numpy`
    *   `scipy`
    *   `matplotlib` (for graphing)

### Installation

```bash
# Install HackRF tools (Debian/Kali/Ubuntu)
sudo apt update
sudo apt install hackrf

# Install Python dependencies
pip3 install numpy scipy matplotlib
```

## Usage

Run the tool using Python 3:

```bash
python3 HackRFCrack.py [OPTIONS]
```

### 1. Instant Replay Attack
Capture a signal and replay it on demand.

```bash
# Capture on 315 MHz
python3 HackRFCrack.py -i -F 315000000
```
*   Press `Ctrl+C` to stop capturing.
*   The tool will ask if you want to Replay (`y`) or Analyze (`a`) the capture.

### 2. Signal Analysis
Demodulate and analyze an existing IQ capture file.

```bash
# Analyze a file with 2000 baud rate (default)
python3 HackRFCrack.py -a capture.iq -B 2000
```
*   Generates a PNG plot showing the raw envelope, filtered signal, and demodulated bits.
*   Prints the decoded binary and hex data to the console.

### 3. Jamming
Block signals on a specific frequency.

```bash
# Jam 433.92 MHz
python3 HackRFCrack.py -j -F 433920000
```

## Options

| Flag | Description | Default |
| :--- | :--- | :--- |
| `-i`, `--instant_replay` | Record and Replay Signal | |
| `-j`, `--jammer` | Jam a frequency | |
| `-a FILE`, `--analyze FILE` | Analyze an existing capture file | |
| `-F FREQ`, `--frequency FREQ` | Frequency in Hz | `315000000` |
| `-S RATE`, `--sample_rate RATE` | Sample Rate | `2000000` |
| `-B RATE`, `--baud_rate RATE` | Baud/Bit Rate for analysis | `2000` |

## Disclaimer
This tool is for educational and authorized testing purposes only. Users are responsible for complying with local radio frequency regulations.
