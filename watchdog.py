"""
watchdog.py – Monitors the trading bot and restarts it if it crashes.
Uses the virtual environment Python to ensure all dependencies are available.
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

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(BASE_DIR, 'venv', 'Scripts', 'python.exe')
BOT_SCRIPT = os.path.join(BASE_DIR, 'auto_trader_exness.py')

RESTART_DELAY = 10          # seconds to wait before restart
MAX_CONSECUTIVE_CRASHES = 5 # stop watchdog if this many crashes happen quickly
CRASH_WINDOW = 300          # seconds (5 minutes)

crashes = []   # timestamps of recent crashes

while True:
    logger.info("🚀 Starting trading bot...")
    process = subprocess.Popen(
        [VENV_PYTHON, BOT_SCRIPT],
        cwd=BASE_DIR
    )

    # Wait for the process to finish
    exit_code = process.wait()
    crash_time = time.time()
    crashes.append(crash_time)

    # Remove crashes older than the window
    crashes = [t for t in crashes if crash_time - t < CRASH_WINDOW]

    logger.warning(f"⚠️ Bot exited with code {exit_code}.")

    if len(crashes) >= MAX_CONSECUTIVE_CRASHES:
        logger.error(
            f"❌ {MAX_CONSECUTIVE_CRASHES} crashes within {CRASH_WINDOW} seconds. "
            "Watchdog shutting down to prevent infinite restart loop."
        )
        sys.exit(1)

    logger.info(f"🔄 Restarting in {RESTART_DELAY} seconds...")
    time.sleep(RESTART_DELAY)