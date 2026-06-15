import json
from datetime import datetime

signals = [
    {"pair": "EURUSD", "signal": "BUY", "confidence": 0.78, "strength": "STRONG", "entry": 1.0925, "stop_loss": 1.09025, "take_profit": 1.09625, "risk_reward": 1.67, "timestamp": datetime.now().isoformat()},
    {"pair": "GBPUSD", "signal": "SELL", "confidence": 0.72, "strength": "MEDIUM", "entry": 1.2650, "stop_loss": 1.26725, "take_profit": 1.26125, "risk_reward": 1.67, "timestamp": datetime.now().isoformat()},
    {"pair": "USDJPY", "signal": "BUY", "confidence": 0.80, "strength": "STRONG", "entry": 148.50, "stop_loss": 148.488, "take_profit": 148.52, "risk_reward": 1.67, "timestamp": datetime.now().isoformat()},
    {"pair": "AUDUSD", "signal": "SELL", "confidence": 0.65, "strength": "MEDIUM", "entry": 0.6580, "stop_loss": 0.6598, "take_profit": 0.6550, "risk_reward": 1.67, "timestamp": datetime.now().isoformat()},
    {"pair": "USDCAD", "signal": "BUY", "confidence": 0.75, "strength": "STRONG", "entry": 1.3540, "stop_loss": 1.3522, "take_profit": 1.3570, "risk_reward": 1.67, "timestamp": datetime.now().isoformat()}
]

print(json.dumps(signals))