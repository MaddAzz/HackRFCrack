#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import subprocess
import os
import sys
import threading
import glob

app = Flask(__name__)

# Global process handle
current_process = None
output_buffer = []

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_process(command):
    global current_process, output_buffer
    if current_process and current_process.poll() is None:
        return False, "A process is already running."

    output_buffer = []
    
    def target():
        global current_process
        try:
            # Run unbuffered
            current_process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1,
                cwd=BASE_DIR
            )
            
            for line in iter(current_process.stdout.readline, ''):
                if line:
                    output_buffer.append(line)
            
            current_process.stdout.close()
            current_process.wait()
            current_process = None
            output_buffer.append("\n[Process Finished]\n")
        except Exception as e:
            output_buffer.append(f"\n[Error] {str(e)}\n")

    t = threading.Thread(target=target)
    t.start()
    return True, "Started"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/files/<path:filename>')
def serve_file(filename):
    return send_from_directory(BASE_DIR, filename)

@app.route('/api/files')
def list_files():
    # List .iq, .png, .json files
    patterns = ["*.iq", "*.png", "*.json"]
    files = []
    for pattern in patterns:
        for f in glob.glob(os.path.join(BASE_DIR, pattern)):
            files.append(os.path.basename(f))
    return jsonify({"files": sorted(files)})

@app.route('/api/stop', methods=['POST'])
def stop_process():
    global current_process
    if current_process and current_process.poll() is None:
        current_process.terminate()
        return jsonify({"status": "Terminated"})
    return jsonify({"status": "No process running"})

@app.route('/api/logs')
def get_logs():
    global output_buffer
    # Return last 100 lines
    return jsonify({"logs": "".join(output_buffer[-100:])})

@app.route('/api/start', methods=['POST'])
def start_tool():
    data = request.json
    tool = data.get('tool')
    freq = data.get('freq', '315000000')
    
    # New Advanced Params
    sample_rate = data.get('sample_rate', '2000000')
    lna = data.get('lna', '16')
    vga = data.get('vga', '20')
    amp = data.get('amp', False)
    
    cmd = []
    base_script = [sys.executable, "HackRFCrack.py"]
    
    # Common Args
    common_args = ["-F", str(freq), "-S", str(sample_rate)]
    gain_args = ["-l", str(lna), "-g", str(vga)]
    if amp:
        gain_args.append("-p")

    if tool == 'jammer':
        cmd = base_script + ["--jammer"] + common_args
    elif tool == 'replay':
        # Replay mode with Gain Control
        cmd = base_script + ["--instant_replay"] + common_args + gain_args
    elif tool == 'salamandra':
        cmd = base_script + ["--salamandra"]
    elif tool == 'drone':
        cmd = base_script + ["--drone"]
    elif tool == 'rtl433':
        cmd = base_script + ["--rtl433"] + common_args
    elif tool == 'analyze':
        filename = data.get('file', 'capture.iq')
        baud = data.get('baud', '2000')
        # Analyze doesn't need frequency/gain, just file/sample_rate/baud
        cmd = base_script + ["--analyze", filename, "-B", str(baud), "-S", str(sample_rate)]
    else:
        return jsonify({"error": "Unknown tool"}), 400
        
    success, msg = run_process(cmd)
    return jsonify({"status": msg})

def start_server():
    print("[*] Web UI running at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    start_server()