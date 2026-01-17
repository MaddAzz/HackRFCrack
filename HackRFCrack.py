#!/usr/bin/env python3
import argparse
import sys
import subprocess
import time
import os
import signal
import json
import numpy as np
from scipy.signal import butter, lfilter, find_peaks
from scipy.fft import fft, fftfreq

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
    Performs ADVANCED OOK demodulation and analysis on a capture file.
    """
    print(f"[*] Analyzing {filename} (Advanced Mode)...")
    iq_data = load_iq_data(filename)
    
    if iq_data is None:
        return

    # --- 1. Signal Processing ---
    envelope = np.abs(iq_data)
    
    # Auto-detect noise floor to set improved threshold
    noise_floor = np.percentile(envelope, 10)
    signal_peak = np.max(envelope)
    threshold = (noise_floor + signal_peak) / 2
    
    # Binary slicing
    binary_signal = (envelope > threshold).astype(int)
    
    # --- 2. Pulse Width Analysis (The "Advanced" Part) ---
    # Find edges
    diff = np.diff(binary_signal)
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    
    # Handle partial pulses at start/end
    if len(ends) > 0 and len(starts) > 0:
        if ends[0] < starts[0]: ends = ends[1:]
        if starts[-1] > ends[-1]: starts = starts[:-1]
    
    pulses = ends - starts
    
    if len(pulses) == 0:
        print("[-] No pulses detected. Signal too weak or empty?")
        return

    # Calculate statistics
    min_pulse = np.min(pulses)
    max_pulse = np.max(pulses)
    avg_pulse = np.mean(pulses)
    
    # Estimate Baud Rate from shortest consistent pulse
    # We look for the 10th percentile to ignore glitches, but be sensitive to short bits
    shortest_pulse_samples = np.percentile(pulses, 10)
    estimated_baud = sample_rate / shortest_pulse_samples
    
    # --- 3. Demodulation ---
    # Use estimated baud if available and reasonable, else user provided
    if 100 < estimated_baud < 20000:
        target_baud = estimated_baud
        print(f"[*] Auto-detected Symbol Rate: ~{int(target_baud)} baud")
    else:
        target_baud = bit_rate
        print(f"[*] Using Default Symbol Rate: {target_baud} baud")

    samples_per_bit = int(sample_rate / target_baud)
    
    # Center sampling
    demodulated_bits = binary_signal[samples_per_bit//2::samples_per_bit]
    bit_str = "".join(map(str, demodulated_bits))

    # --- 4. Reporting ---
    print("\n" + "="*40)
    print("      ADVANCED SIGNAL ANALYSIS      ")
    print("="*40)
    print(f"File Size:       {len(iq_data)} samples")
    print(f"Duration:        {len(iq_data)/sample_rate:.4f} seconds")
    print(f"Noise Floor:     {noise_floor:.4f}")
    print(f"Signal Peak:     {signal_peak:.4f}")
    print(f"Threshold:       {threshold:.4f}")
    print(f"Pulses Detected: {len(pulses)}")
    print(f"Shortest Pulse:  {min_pulse} samples ({min_pulse/sample_rate*1000000:.1f} µs)")
    print(f"Longest Pulse:   {max_pulse} samples ({max_pulse/sample_rate*1000000:.1f} µs)")
    print(f"Est. Baud Rate:  {int(target_baud)} Hz")
    print("-"*40)
    print("RAW DATA (First 64 bits):")
    print(bit_str[:64])
    print("-"*40)
    
    # Export JSON for Web UI
    analysis_data = {
        "filename": filename,
        "duration": len(iq_data)/sample_rate,
        "baud_rate": int(target_baud),
        "pulses_count": len(pulses),
        "min_pulse_us": min_pulse/sample_rate*1000000,
        "raw_bits": bit_str[:512], # Limit for JSON
        "hex_preview": "..." 
    }
    
    try:
        hex_val = hex(int(bit_str[:len(bit_str)//8*8], 2))
        analysis_data["hex_preview"] = hex_val[:100]
        print(f"HEX (Start): {hex_val[:66]}...")
    except:
        pass

    with open(f"{filename}.json", "w") as f:
        json.dump(analysis_data, f, indent=4)
        print(f"[*] Data saved to {filename}.json")

    # --- 5. Advanced Plotting ---
    if PLOT_AVAILABLE:
        print("[*] Generating advanced spectrogram/plots...")
        plt.figure(figsize=(14, 10))
        
        # Subplot 1: Time Domain (Envelope)
        plt.subplot(3, 1, 1)
        plot_len = min(20000, len(envelope))
        t = np.arange(plot_len) / sample_rate
        plt.plot(t, envelope[:plot_len], color='cyan', lw=1)
        plt.axhline(threshold, color='red', linestyle='--', alpha=0.7)
        plt.title('Time Domain: Signal Envelope')
        plt.ylabel('Amplitude')
        plt.grid(True, alpha=0.3)
        plt.gca().set_facecolor('#111')

        # Subplot 2: Pulse Width Histogram
        plt.subplot(3, 1, 2)
        plt.hist(pulses, bins=50, color='lime', alpha=0.7)
        plt.title('Pulse Width Histogram (Distribution of High States)')
        plt.xlabel('Duration (Samples)')
        plt.ylabel('Count')
        plt.grid(True, alpha=0.3)
        plt.gca().set_facecolor('#111')

        # Subplot 3: Frequency Domain (FFT) - Simple Center Slice
        plt.subplot(3, 1, 3)
        fft_n = 1024
        if len(iq_data) > fft_n:
            # Take a slice from the middle
            mid = len(iq_data) // 2
            slice_iq = iq_data[mid:mid+fft_n]
            # Windowing
            slice_iq = slice_iq * np.blackman(fft_n)
            
            yf = fft(slice_iq)
            xf = fftfreq(fft_n, 1 / sample_rate)
            
            # Shift to center
            yf = np.fft.fftshift(yf)
            xf = np.fft.fftshift(xf)
            
            plt.plot(xf / 1e6, 20 * np.log10(np.abs(yf)), color='yellow')
            plt.title('Frequency Domain (FFT snapshot)')
            plt.xlabel('Frequency Offset (MHz)')
            plt.ylabel('dB')
            plt.grid(True, alpha=0.3)
            plt.gca().set_facecolor('#111')

        plt.tight_layout()
        plt.savefig(f"{filename}_analysis.png", facecolor='#222', edgecolor='none')
        print(f"[*] Advanced Plot saved to {filename}_analysis.png")


def replay_attack(freq, sample_rate=2000000, lna=16, vga=20, amp=False):
    capture_file = "capture.iq"
    
    print(f"[*] Starting Capture on {freq/1000000} MHz...")
    print(f"[*] Settings: LNA={lna}, VGA={vga}, Amp={'ON' if amp else 'OFF'}")
    print("[*] Press Ctrl+C to stop capturing and start transmitting.")
    
    amp_opt = "-a 1" if amp else "-a 0"
    
    # Capture
    cmd = f"hackrf_transfer -r {capture_file} -f {freq} -s {sample_rate} {amp_opt} -l {lna} -g {vga}"
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
            # Transmit (Using high gain for TX usually: -x 47)
            # You might want TX gain control too, but for now max is standard for jamming/replay.
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

def jammer(freq, sample_rate=2000000, noise_type="white"):
    print(f"[*] Starting Jammer on {freq/1000000} MHz ({noise_type})...")
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
    parser.add_argument("-l", "--lna_gain", type=int, default=16, help="RX LNA (IF) Gain 0-40dB (default: 16)")
    parser.add_argument("-g", "--vga_gain", type=int, default=20, help="RX VGA (Baseband) Gain 0-62dB (default: 20)")
    parser.add_argument("-p", "--amp_enable", action='store_true', help="Enable RF Amplifier (14dB)")
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
        # Pass gains to replay function
        replay_attack(args.frequency, args.sample_rate, args.lna_gain, args.vga_gain, args.amp_enable)
    elif args.jammer:
        jammer(args.frequency, args.sample_rate)
    elif args.analyze:
        analyze_signal(args.analyze, args.sample_rate, args.baud_rate)
    elif args.webui:
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
