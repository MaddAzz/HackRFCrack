#!/usr/bin/env python3
import subprocess
import sys
import time
import os
import argparse
from datetime import datetime

# ASCII Art
print(r'''
    ____                         ____       __            __
   / __ \_________  ____  ___   / __ \___  / /____  _____/ /
  / / / / ___/ __ \/ __ \/ _ \ / / / / _ \/ __/ _ \/ ___/ /
 / /_/ / /  / /_/ / / / /  __// /_/ /  __/ /_/  __/ /__/ /
/_____/_/   \____/_/ /_/\___//_____/\___/\__/
                                          HACKRF EDITION
''')

def run_sweep(freq_min, freq_max, bin_width=1000000):
    """
    Runs hackrf_sweep for a specific range.
    """
    # hackrf_sweep takes frequencies in MHz
    freq_min_mhz = int(freq_min / 1000000)
    freq_max_mhz = int(freq_max / 1000000)

    cmd = [
        "hackrf_sweep",
        "-f", f"{freq_min_mhz}:{freq_max_mhz}",
        "-w", str(bin_width),
        "-1"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip().split('\n') if result.returncode == 0 else []
    except FileNotFoundError:
        return []

def analyze_drone_bands(threshold_dbm=-50):
    """
    Scans 2.4GHz and 5.8GHz bands for high power signals.
    """
    # Drone Bands
    # 2.4 GHz: 2400 - 2483.5 MHz
    # 5.8 GHz: 5725 - 5875 MHz
    
    bands = [
        ("2.4GHz ISM", 2400000000, 2483500000),
        ("5.8GHz ISM", 5725000000, 5875000000)
    ]
    
    detected_signals = []
    
    for name, f_min, f_max in bands:
        lines = run_sweep(f_min, f_max)
        
        for line in lines:
            parts = line.split(', ')
            if len(parts) < 7: continue
            
            try:
                hz_low = int(parts[2])
                bin_width = int(parts[4])
                dbm_vals = [float(x) for x in parts[6:]]
                
                for i, dbm in enumerate(dbm_vals):
                    if dbm > threshold_dbm:
                        freq = hz_low + (i * bin_width)
                        detected_signals.append({
                            "freq": freq,
                            "dbm": dbm,
                            "band": name
                        })
            except ValueError:
                continue
                
    return detected_signals

def main():
    parser = argparse.ArgumentParser(description="DroneDetect - UAV Identification for HackRF")
    parser.add_argument("-t", "--threshold", type=float, default=-50, help="Signal threshold in dBm (default: -50)")
    args = parser.parse_args()
    
    print(f"[*] Monitoring Drone Bands (Threshold: {args.threshold} dBm)...")
    print("[*] Press Ctrl+C to stop.")
    
    try:
        while True:
            signals = analyze_drone_bands(args.threshold)
            
            # Clear screen (optional, or just print log)
            # os.system('cls' if os.name == 'nt' else 'clear') 
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if signals:
                # Group by proximity to identify wideband signals (like OcuSync/Lightbridge)
                # Simple logic: If many hits are close together, it's likely a drone video feed.
                
                print(f"[{timestamp}] ALERT: {len(signals)} signals detected!")
                
                # Sort by power
                signals.sort(key=lambda x: x['dbm'], reverse=True)
                
                # Display top 5 strongest
                for s in signals[:5]:
                    f_mhz = s['freq'] / 1e6
                    print(f"   -> {s['band']}: {f_mhz:.1f} MHz @ {s['dbm']:.1f} dBm")
                    
                if len(signals) > 10:
                    print("   [!] High density of signals - Possible Video Link / Hopping Controller")
                
            else:
                sys.stdout.write(f"\r[{timestamp}] Scanning... No targets found.")
                sys.stdout.flush()
                
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[*] Surveillance stopped.")

if __name__ == "__main__":
    main()
