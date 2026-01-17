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
    print("-