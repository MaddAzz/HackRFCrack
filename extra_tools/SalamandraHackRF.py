#!/usr/bin/env python3
import subprocess
import sys
import time
import os
import argparse
import csv
import math

# ASCII Art
print(r'''
   _____       __                                 __
  / ___/____ _/ /___ _____ ___  ____ _____  ____/ /_________ _
  \__ \/ __ `/ / __ `/ __ `__ \/ __ `/ __ \/ __  / ___/ __ `/
 ___/ / /_/ / / /_/ / / / / / / /_/ / / / / /_/ / /  / /_/ /
/____/\__,_/_/\__,_/_/ /_/ /_/\__,_/_/ /_/\__,_/_/   \__,_/
                                    HACKRF EDITION
''')

def run_sweep(freq_min, freq_max, sample_rate=20000000, bin_width=1000000):
    """
    Runs hackrf_sweep and returns the output as a list of lines.
    freq_min, freq_max in Hz.
    """
    # hackrf_sweep takes frequencies in MHz
    freq_min_mhz = int(freq_min / 1000000)
    freq_max_mhz = int(freq_max / 1000000)

    cmd = [
        "hackrf_sweep",
        "-f", f"{freq_min_mhz}:{freq_max_mhz}",
        "-w", str(bin_width),
        "-1" # Single sweep
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running hackrf_sweep: {result.stderr}")
            return []
        return result.stdout.strip().split('\n')
    except FileNotFoundError:
        print("Error: hackrf_sweep not found. Please install hackrf tools.")
        sys.exit(1)

def analyze_sweep_data(sweep_output, threshold_dbm=-40):
    """
    Parses sweep output and detects signals above threshold.
    Returns a list of potential hits: (frequency_hz, dbm)
    """
    hits = []
    
    for line in sweep_output:
        parts = line.split(', ')
        if len(parts) < 7:
            continue
            
        try:
            hz_low = int(parts[2])
            hz_high = int(parts[3])
            bin_width = int(parts[4])
            
            # dBm values start from index 6
            dbm_values = [float(x) for x in parts[6:]]
            
            for i, dbm in enumerate(dbm_values):
                if dbm > threshold_dbm:
                    freq = hz_low + (i * bin_width)
                    hits.append((freq, dbm))
                    
        except ValueError:
            continue
            
    return hits

def main():
    parser = argparse.ArgumentParser(description="Salamandra - Spy Microphone Detector for HackRF")
    parser.add_argument("-t", "--threshold", type=float, default=-40, help="Signal threshold in dBm (default: -40)")
    parser.add_argument("-m", "--monitor", action="store_true", help="Continuous monitoring mode")
    
    args = parser.parse_args()
    
    # Common Bug Frequencies (in Hz)
    # Range 1: VHF/UHF Lower (common for cheap analog bugs): 30MHz - 500MHz
    # Range 2: UHF Higher (Pro bugs, GSM/DECT lookalikes): 800MHz - 1200MHz
    ranges = [
        (30000000, 500000000),   # 30-500 MHz
        (800000000, 1200000000) # 800-1200 MHz
    ]
    
    print(f"[*] Starting Scan with Threshold: {args.threshold} dBm")
    
    try:
        while True:
            all_hits = []
            print(f"\n[*] Sweeping...")
            
            for r_min, r_max in ranges:
                # print(f"    Scanning {r_min/1e6} - {r_max/1e6} MHz...")
                data = run_sweep(r_min, r_max)
                hits = analyze_sweep_data(data, args.threshold)
                all_hits.extend(hits)
            
            # Sort by power (strongest first)
            all_hits.sort(key=lambda x: x[1], reverse=True)
            
            if all_hits:
                print(f"\n[!] POTENTIAL SIGNALS DETECTED: {len(all_hits)}")
                print("-" * 50)
                print(f"{ 'FREQUENCY (MHz)':<20} | {'POWER (dBm)':<15} | {'DESCRIPTION'}")
                print("-" * 50)
                
                displayed = 0
                for freq, dbm in all_hits:
                    if displayed > 15: # Show max 15 strongest
                        break
                    
                    desc = "Unknown"
                    f_mhz = freq / 1e6
                    
                    if 88 <= f_mhz <= 108: desc = "FM Radio Band"
                    elif 108 <= f_mhz <= 137: desc = "Airband"
                    elif 137 <= f_mhz <= 174: desc = "VHF / 2m Band"
                    elif 400 <= f_mhz <= 470: desc = "UHF / 70cm Band"
                    elif 850 <= f_mhz <= 950: desc = "GSM/LTE Low"
                    elif 1090 <= f_mhz <= 1100: desc = "ADS-B (Aircraft)"
                    
                    print(f"{f_mhz:<20.3f} | {dbm:<15.1f} | {desc}")
                    displayed += 1
            else:
                print("[-] No suspicious signals found above threshold.")
            
            if not args.monitor:
                break
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n[*] Stopping...")

if __name__ == "__main__":
    main()
