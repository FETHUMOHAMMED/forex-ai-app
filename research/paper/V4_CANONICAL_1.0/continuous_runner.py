"""CONTINUOUS RUNNER - Persistent candle deduplication."""
import sys
import time
import json
import os
import concurrent.futures
from pathlib import Path
from datetime import datetime, timezone, timedelta


def with_timeout(fn, timeout_sec=15, default=None):
    """Run fn() with a hard timeout. Returns default on timeout."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(fn)
        try:
            return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            print(f"[TIMEOUT] {fn} exceeded {timeout_sec}s")
            return default
        except Exception as e:
            print(f"[TIMEOUT_WRAPPER] exception: {e}")
            return default

class ContinuousPaperRunner:
    def __init__(self):
        self.base_dir = Path("research/paper/V4_CANONICAL_1.0")
        self.signal_log = self.base_dir / "signal_log.jsonl"
        self.runner_log = self.base_dir / "runner_log.jsonl"
        self.evidence_file = self.base_dir / "evidence" / "evaluations.jsonl"
        self.state_file = self.base_dir / "runner_state.json"
        self.evidence_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.pid = os.getpid()
        
        # Load or initialize state
        self.state = self.load_state()
        self.evaluation_count = self.state.get("total_evaluations", 0)
        self.evaluated_candles = set(self.state.get("evaluated_candles", []))

    def load_state(self):
        """Load persistent state from file."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {"total_evaluations": 0, "evaluated_candles": []}

    def save_state(self):
        """Save state to file for persistence."""
        self.state["total_evaluations"] = self.evaluation_count
        self.state["evaluated_candles"] = list(self.evaluated_candles)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def log_operational(self, message):
        entry = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "type": "RUNNER", "pid": self.pid, "message": message}
        with open(self.runner_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        print(f"[RUNNER] {message}")

    def get_current_h4_candle_time(self):
        """Get current H4 candle close time (UTC)."""
        now = datetime.now(timezone.utc)
        candle_hour = (now.hour // 4) * 4
        return now.replace(hour=candle_hour, minute=0, second=0, microsecond=0)

    def should_evaluate(self):
        """Check if this H4 candle has already been evaluated."""
        current_candle = self.get_current_h4_candle_time()
        candle_id = f"V4-USDJPYm-H4-{current_candle.isoformat()}"
        
        if candle_id in self.evaluated_candles:
            return False, None
        
        return True, candle_id

    def evaluate_signal(self, candle_id, candle_time):
        import MetaTrader5 as mt5
        import pandas as pd

        init_ok = with_timeout(mt5.initialize, timeout_sec=10, default=False)
        if not init_ok:
            return {
                "signal": False,
                "reason": "MT5_INIT_FAILED_OR_TIMEOUT",
                "timestamp_utc": candle_time.isoformat(),
                "evaluation_id": candle_id,
                "fvg_detected": False,
                "bias": "UNKNOWN",
                "decision": "ERROR",
            }

        rates = with_timeout(
            lambda: mt5.copy_rates_from_pos("USDJPYm", mt5.TIMEFRAME_H4, 0, 200),
            timeout_sec=15,
            default=None,
        )

        with_timeout(mt5.shutdown, timeout_sec=5, default=None)

        if rates is None or len(rates) < 50:
            return {
                "signal": False,
                "reason": "INSUFFICIENT_DATA",
                "timestamp_utc": candle_time.isoformat(),
                "evaluation_id": candle_id,
                "fvg_detected": False,
                "bias": "UNKNOWN",
                "decision": "ERROR",
            }

        data = pd.DataFrame(rates)
        data['timestamp'] = pd.to_datetime(data['time'], unit='s')

        data['ema_50'] = data['close'].ewm(span=50).mean()
        data['ema_200'] = data['close'].ewm(span=200).mean() if len(data) >= 200 else data['close'].ewm(span=50).mean()

        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        data['atr'] = tr.rolling(14).mean()

        last = data.iloc[-1]
        candle_1 = data.iloc[-3] if len(data) >= 3 else data.iloc[0]

        fvg_detected = candle_1['high'] < last['low']
        bullish_bias = last['ema_50'] > last['ema_200']
        current_hour = datetime.now(timezone.utc).hour
        london_session = 7 <= current_hour < 11

        if fvg_detected and bullish_bias and london_session:
            decision = "TRADE"
            reason = "VALID_BUY_SETUP"
        elif not fvg_detected:
            decision = "REJECT"
            reason = "NO_FVG"
        elif not bullish_bias:
            decision = "REJECT"
            reason = "NO_BULLISH_BIAS"
        elif not london_session:
            decision = "REJECT"
            reason = "OUTSIDE_LONDON"
        else:
            decision = "REJECT"
            reason = "UNKNOWN"

        return {
            "timestamp_utc": candle_time.isoformat(),
            "strategy_version": "V4_CANONICAL_1.0",
            "symbol": "USDJPYm",
            "timeframe": "H4",
            "candle_close_time": candle_time.isoformat(),
            "evaluation_id": candle_id,
            "current_price": last['close'],
            "atr": last['atr'] if pd.notna(last['atr']) else None,
            "ema_50": last['ema_50'],
            "ema_200": last['ema_200'],
            "bias": "BULLISH" if bullish_bias else "BEARISH",
            "fvg_detected": bool(fvg_detected),
            "session": "LONDON" if london_session else "OTHER",
            "direction": "BUY",
            "risk_percent": 0.25,
            "decision": decision,
            "reason": reason,
            "signal": decision == "TRADE"
        }

    def write_signal_log(self, result):
        entry = {
            "timestamp_utc": result["timestamp_utc"],
            "strategy_version": "V4_CANONICAL_1.0",
            "evaluation_number": self.evaluation_count,
            "evaluation_id": result["evaluation_id"],
            "signal": result["signal"],
            "reason": result["reason"],
            "fvg_detected": result["fvg_detected"],
            "bullish_bias": result["bias"] == "BULLISH"
        }
        with open(self.signal_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def write_evidence(self, result):
        with open(self.evidence_file, 'a') as f:
            f.write(json.dumps(result) + '\n')

    def run_continuous(self):
        print("="*70)
        print("  CONTINUOUS PAPER TRADER (PERSISTENT)")
        print("="*70)
        print(f"  Total evaluations so far: {self.evaluation_count}")
        print(f"  Evaluated candles: {len(self.evaluated_candles)}")
        print("="*70)

        self.log_operational(f"Started (PID: {self.pid}) - persistent state loaded")

        try:
            while True:
                should_eval, candle_id = self.should_evaluate()

                if should_eval and candle_id:
                    candle_time = self.get_current_h4_candle_time()
                    self.evaluation_count += 1
                    self.evaluated_candles.add(candle_id)

                    self.log_operational(f"Evaluation #{self.evaluation_count} (candle: {candle_time})")

                    try:
                        result = self.evaluate_signal(candle_id, candle_time)
                    except Exception as e:
                        self.log_operational(f"Exception in evaluate_signal: {e}")
                        result = {
                            "signal": False,
                            "reason": f"EVAL_ERROR: {e}",
                            "evaluation_id": candle_id,
                            "fvg_detected": False,
                            "bias": "UNKNOWN",
                            "decision": "ERROR",
                            "timestamp_utc": candle_time.isoformat(),
                        }

                    try:
                        self.write_signal_log(result)
                        self.write_evidence(result)
                        self.save_state()
                    except Exception as e:
                        self.log_operational(f"Exception in write: {e}")

                    self.log_operational(f"Decision: {result.get('decision', 'ERROR')}")
                    self.log_operational(f"Reason: {result.get('reason', 'UNKNOWN')}")

                # Heartbeat every loop (every 60s) — proves process is alive
                self.log_operational("HEARTBEAT")

                time.sleep(60)

        except KeyboardInterrupt:
            self.save_state()
            self.log_operational(f"Stopped. Total evaluations: {self.evaluation_count}")

if __name__ == "__main__":
    runner = ContinuousPaperRunner()
    runner.run_continuous()
