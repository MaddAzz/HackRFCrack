#!/usr/bin/env python3
from flask import Flask, render_template, request, jsonify, Response
import subprocess
import os
import sys
import threading
import time
import signal

app = Flask(__name__)

# Global process handle
current_process = None
output_buffer = []

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
                cwd=os.path.dirname(os.path.abspath(__file__))
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
    # Return last N lines to avoid huge payloads, or implement cursor
    return jsonify({"logs": "".join(output_buffer[-50:])})

@app.route('/api/start', methods=['POST'])
def start_tool():
    data = request.json
    tool = data.get('tool')
    freq = data.get('freq', '315000000')
    
    cmd = []
    
    # Base command: python3 HackRFCrack.py ...
    base_script = [sys.executable, "HackRFCrack.py"]
    
    if tool == 'jammer':
        cmd = base_script + ["--jammer", "-F", str(freq)]
    elif tool == 'replay':
        # Replay in Web UI is tricky because of input(). 
        # For now, we'll just support capture or fixed replay if we modify the script.
        # Simplest: Just run capture mode.
        cmd = base_script + ["--instant_replay", "-F", str(freq)]
    elif tool == 'salamandra':
        cmd = base_script + ["--salamandra"]
    elif tool == 'drone':
        cmd = base_script + ["--drone"]
    elif tool == 'rtl433':
        cmd = base_script + ["--rtl433", "-F", str(freq)]
    else:
        return jsonify({"error": "Unknown tool"}), 400
        
    success, msg = run_process(cmd)
    return jsonify({"status": msg})

def start_server():
    print("[*] Web UI running at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    start_server()
