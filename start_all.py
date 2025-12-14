#!/usr/bin/env python3
"""
Multi-service startup script for Railway deployment.
Runs both Chordis API and ChordMini in the same container.
"""

import subprocess
import sys
import os
import time
import signal
import threading

# Get port from Railway environment
PORT = int(os.environ.get("PORT", 5000))
CHORDMINI_PORT = 5001

processes = []

def log(msg):
    print(f"[STARTUP] {msg}", flush=True)

def run_chordmini():
    """Start ChordMini service on port 5001"""
    chordmini_path = os.path.join(os.path.dirname(__file__), 'chordmini', 'python_backend')
    
    if not os.path.exists(os.path.join(chordmini_path, 'app_factory.py')):
        log(f"ChordMini not found at {chordmini_path}")
        return None
    
    log(f"Starting ChordMini on port {CHORDMINI_PORT}...")
    
    env = os.environ.copy()
    env['PORT'] = str(CHORDMINI_PORT)
    
    process = subprocess.Popen(
        [sys.executable, '-c', 
         'from app_factory import create_app; app = create_app(); app.run(host="0.0.0.0", port=5001, debug=False)'],
        cwd=chordmini_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    
    # Log ChordMini output in background
    def log_output():
        for line in iter(process.stdout.readline, b''):
            print(f"[CHORDMINI] {line.decode().strip()}", flush=True)
    
    threading.Thread(target=log_output, daemon=True).start()
    
    return process

def run_main_api():
    """Start main Chordis API using gunicorn"""
    log(f"Starting Chordis API on port {PORT}...")
    
    process = subprocess.Popen(
        ['gunicorn', 'api:app', 
         '--bind', f'0.0.0.0:{PORT}',
         '--workers', '2',
         '--timeout', '120',
         '--access-logfile', '-',
         '--error-logfile', '-'],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    
    return process

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    log("Received shutdown signal, stopping services...")
    for p in processes:
        if p and p.poll() is None:
            p.terminate()
    sys.exit(0)

def main():
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    log("=" * 50)
    log("CHORDIS MULTI-SERVICE STARTUP")
    log("=" * 50)
    
    # Start ChordMini first
    chordmini_proc = run_chordmini()
    if chordmini_proc:
        processes.append(chordmini_proc)
        log("Waiting for ChordMini to initialize...")
        time.sleep(5)
    
    # Start main API
    main_proc = run_main_api()
    processes.append(main_proc)
    
    log("=" * 50)
    log("All services started!")
    log(f"  - Chordis API: http://localhost:{PORT}")
    if chordmini_proc:
        log(f"  - ChordMini: http://localhost:{CHORDMINI_PORT}")
    log("=" * 50)
    
    # Wait for main process
    try:
        main_proc.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()

