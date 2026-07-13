"""
watchdog.py - Monitors the trading bot and restarts on code changes.
Auto-restarts when any .py file in ai-service/ or institutional/ changes.
"""

import subprocess
import time
import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(BASE_DIR, 'venv', 'Scripts', 'python.exe')
BOT_SCRIPT = os.path.join(BASE_DIR, 'auto_trader_exness.py')
ROOT_DIR = os.path.dirname(BASE_DIR)

RESTART_DELAY = 5
MAX_CRASHES = 10
CRASH_WINDOW = 300

def get_file_times():
    """Get modification times of all Python files in the project"""
    times = {}
    for folder in ['ai-service', 'institutional']:
        path = os.path.join(ROOT_DIR, folder)
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                if '__pycache__' in root:
                    continue
                for f in files:
                    if f.endswith('.py'):
                        full = os.path.join(root, f)
                        times[full] = os.path.getmtime(full)
    return times

crashes = []
last_file_times = get_file_times()
process = None

logger.info("Watchdog started - monitoring code changes...")

while True:
    # Check if any Python file changed
    current_times = get_file_times()
    changed_files = []
    for fpath, mtime in current_times.items():
        if fpath not in last_file_times or mtime > last_file_times[fpath]:
            changed_files.append(fpath)
    
    if changed_files and process and process.poll() is None:
        logger.info(f"Code change detected in {len(changed_files)} files, restarting bot...")
        for f in changed_files[:3]:
            logger.info(f"  Changed: {os.path.basename(f)}")
        process.terminate()
        try:
            process.wait(timeout=5)
        except:
            process.kill()
            process.wait()
        time.sleep(2)
        # Clear Python caches
        for root, dirs, files in os.walk(ROOT_DIR):
            if '__pycache__' in dirs:
                cache_path = os.path.join(root, '__pycache__')
                for cf in os.listdir(cache_path):
                    if cf.endswith('.pyc'):
                        os.remove(os.path.join(cache_path, cf))
        logger.info("Caches cleared, restarting...")
    
    last_file_times = current_times
    
    if process is None or process.poll() is not None:
        if process and process.poll() is not None:
            exit_code = process.poll()
            crash_time = time.time()
            crashes.append(crash_time)
            crashes = [t for t in crashes if crash_time - t < CRASH_WINDOW]
            logger.warning(f"Bot exited with code {exit_code}")
            
            if len(crashes) >= MAX_CRASHES:
                logger.error(f"Too many crashes - watchdog stopping")
                sys.exit(1)
            
            time.sleep(RESTART_DELAY)
        
        logger.info("Starting trading bot...")
        process = subprocess.Popen(
            [VENV_PYTHON, BOT_SCRIPT],
            cwd=BASE_DIR,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
    
    time.sleep(10)
