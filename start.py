#!/usr/bin/env python3
"""
Startup script for Chordis + ChordMini on Railway
Starts both the main API and ChordMini backend
"""

import os
import sys
import subprocess
import time
import signal
import threading

# Get port from environment
PORT = int(os.environ.get("PORT", 5000))
CHORDMINI_PORT = 5001

processes = []

def start_chordmini():
    """Start ChordMini backend in background"""
    chordmini_path = os.path.join(os.path.dirname(__file__), 'chordmini', 'python_backend')
    app_factory = os.path.join(chordmini_path, 'app_factory.py')
    
    if not os.path.exists(app_factory):
        print(f"[STARTUP] ChordMini not found at {chordmini_path}")
        return None
    
    print(f"[STARTUP] Starting ChordMini on port {CHORDMINI_PORT}...")
    
    env = os.environ.copy()
    env['FLASK_APP'] = 'app_factory:create_app'
    env['PORT'] = str(CHORDMINI_PORT)
    
    try:
        # Start ChordMini using gunicorn
        process = subprocess.Popen(
            [
                sys.executable, '-m', 'gunicorn',
                'app_factory:create_app()',
                '--bind', f'0.0.0.0:{CHORDMINI_PORT}',
                '--workers', '1',
                '--timeout', '300',
                '--chdir', chordmini_path
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=chordmini_path
        )
        processes.append(process)
        print(f"[STARTUP] ChordMini started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"[STARTUP] Failed to start ChordMini: {e}")
        return None

def start_main_api():
    """Start main Chordis API"""
    print(f"[STARTUP] Starting main API on port {PORT}...")
    
    process = subprocess.Popen(
        [
            sys.executable, '-m', 'gunicorn',
            'api:app',
            '--bind', f'0.0.0.0:{PORT}',
            '--workers', '2',
            '--timeout', '120'
        ],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    processes.append(process)
    print(f"[STARTUP] Main API started (PID: {process.pid})")
    return process

def cleanup(signum=None, frame=None):
    """Clean up all processes"""
    print("\n[STARTUP] Shutting down...")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            proc.kill()
    sys.exit(0)

def main():
    # Set up signal handlers
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    
    print("=" * 50)
    print("CHORDIS + CHORDMINI STARTUP")
    print("=" * 50)
    
    # Start ChordMini first (in background thread to not block)
    chordmini_thread = threading.Thread(target=start_chordmini)
    chordmini_thread.start()
    
    # Give ChordMini a moment to start
    time.sleep(3)
    
    # Start main API (this will block)
    main_process = start_main_api()
    
    # Wait for main process
    try:
        main_process.wait()
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()

