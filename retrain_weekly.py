"""
Weekly automated model retraining script.
Fetches recent MT5 data, retrains XGBoost models, and saves them.
"""

import os
import sys
import logging
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from train_from_mt5 import MT5DataTrainer

# Set up logging to file
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"retrain_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("Starting scheduled model retraining...")
    logger.info("=" * 60)
    
    try:
        trainer = MT5DataTrainer()
        trainer.run()
        logger.info("✅ Retraining completed successfully.")
    except Exception as e:
        logger.error(f"❌ Retraining failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()