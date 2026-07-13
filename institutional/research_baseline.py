"""
RESEARCH BASELINE - Pre-Volume 9 Snapshot
Captured: 2026-07-10
Purpose: Compare performance before/after Volume 9 optimization
"""
from dataclasses import dataclass

@dataclass
class Baseline:
    capture_date: str = "2026-07-10"
    total_data_points: int = 157
    real_trades: int = 45
    shadow_trades: int = 112

    def __post_init__(self):
        self.regime_stats = {
            "RANGING": {"trades": 69, "win_rate": 54.0, "avg_confidence": 0.570},
            "BREAKOUT": {"trades": 43, "win_rate": 30.0, "avg_confidence": 0.591},
        }
        self.pair_stats = {
            "USDJPY": {"trades": 10, "win_rate": 70.0, "rec": "KEEP"},
            "NZDUSD": {"trades": 29, "win_rate": 52.0, "rec": "KEEP"},
            "EURUSD": {"trades": 20, "win_rate": 45.0, "rec": "KEEP"},
            "GBPUSD": {"trades": 22, "win_rate": 41.0, "rec": "KEEP"},
            "USDCAD": {"trades": 10, "win_rate": 40.0, "rec": "KEEP"},
            "AUDUSD": {"trades": 21, "win_rate": 29.0, "rec": "DROP"},
        }
        self.best_combos = [
            {"regime": "RANGING", "pair": "NZDUSD", "trades": 15, "win_rate": 80.0},
            {"regime": "RANGING", "pair": "USDJPY", "trades": 7, "win_rate": 71.0},
            {"regime": "RANGING", "pair": "EURUSD", "trades": 11, "win_rate": 55.0},
        ]
        self.confidence_stats = {
            "0.53-0.56": {"trades": 28, "win_rate": 39.0},
            "0.56-0.60": {"trades": 67, "win_rate": 43.0},
            "0.60-0.70": {"trades": 17, "win_rate": 59.0},
        }
        self.grade_stats = {
            "A": {"trades": 17, "win_rate": 59.0},
            "B": {"trades": 95, "win_rate": 42.0},
        }
        self.recommendations = [
            "1. RANGING regime: +15% confidence boost",
            "2. BREAKOUT regime: -20% penalty, likely SKIP",
            "3. USDJPY + RANGING: maximum allocation",
            "4. NZDUSD + RANGING: high allocation (80% WR)",
            "5. AUDUSD: DROP from active pairs (29% WR)",
            "6. NZDUSD + BREAKOUT: BLOCK (21% WR)",
            "7. Grade A only: 59% WR target",
            "8. Confidence 0.60+: best performing bracket",
            "9. Session: London + Asian only",
        ]

    def summary(self):
        print("=" * 60)
        print("  RESEARCH BASELINE - " + self.capture_date)
        print("=" * 60)
        print("  Data: " + str(self.total_data_points) + " points (" + str(self.real_trades) + " real + " + str(self.shadow_trades) + " shadow)")
        print()
        print("  Best regime:  RANGING (" + str(self.regime_stats["RANGING"]["win_rate"]) + "% WR)")
        print("  Worst regime: BREAKOUT (" + str(self.regime_stats["BREAKOUT"]["win_rate"]) + "% WR)")
        print()
        print("  Best pair:    USDJPY (" + str(self.pair_stats["USDJPY"]["win_rate"]) + "% WR)")
        print("  Dropped:      AUDUSD (" + str(self.pair_stats["AUDUSD"]["win_rate"]) + "% WR)")
        print()
        print("  Best combo:   NZDUSD + RANGING (" + str(self.best_combos[0]["win_rate"]) + "% WR)")
        print()
        print("  Target WR:    59% (Grade A, 0.60+ confidence)")
        print("=" * 60)


BASELINE = Baseline()

if __name__ == "__main__":
    BASELINE.summary()
