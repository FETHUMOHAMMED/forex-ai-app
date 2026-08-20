"""Real Research Platform - Immutable research records for every strategy version."""
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

class ResearchPhase(str, Enum):
    HYPOTHESIS = "HYPOTHESIS"
    BACKTEST = "BACKTEST"
    WALK_FORWARD = "WALK_FORWARD"
    OUT_OF_SAMPLE = "OUT_OF_SAMPLE"
    PAPER = "PAPER"
    SMALL_LIVE = "SMALL_LIVE"
    STATISTICAL_VALIDATION = "STATISTICAL_VALIDATION"
    PRODUCTION = "PRODUCTION"

@dataclass(frozen=True)
class ResearchRecord:
    """Immutable research record for one strategy version."""
    strategy_version: str          # "V3.1"
    dataset: str                    # "EURUSD 2019-2025"
    train_period: str               # "2019-2023"
    validation_period: str          # "2024"
    oos_period: str                 # "2025"
    total_trades: int
    win_rate: float
    profit_factor: float
    expectancy: float
    sharpe: float
    sortino: float
    max_drawdown: float
    turnover: float
    slippage_sensitivity: float
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    phase: ResearchPhase = ResearchPhase.BACKTEST

class ResearchPlatform:
    """Immutable research records for every strategy version."""
    
    def __init__(self, records_path: str = "packages/research/research_records.json"):
        self.records_path = Path(records_path)
        self.records: Dict[str, ResearchRecord] = {}
        self._load()
    
    def _load(self):
        if self.records_path.exists():
            data = json.loads(self.records_path.read_text())
            for version, record_data in data.items():
                self.records[version] = ResearchRecord(**record_data)
    
    def _save(self):
        data = {v: r.__dict__ for v, r in self.records.items()}
        self.records_path.parent.mkdir(parents=True, exist_ok=True)
        self.records_path.write_text(json.dumps(data, indent=2, default=str))
    
    def register_strategy(self, record: ResearchRecord) -> bool:
        """Register immutable research record. Rejects duplicate versions."""
        if record.strategy_version in self.records:
            print(f"[RESEARCH] Version {record.strategy_version} already exists - IMMUTABLE")
            return False
        self.records[record.strategy_version] = record
        self._save()
        print(f"[RESEARCH] Registered {record.strategy_version}: "
              f"{record.total_trades} trades, PF={record.profit_factor}, "
              f"Sharpe={record.sharpe}")
        return True
    
    def get_record(self, version: str) -> Optional[ResearchRecord]:
        return self.records.get(version)
    
    def compare_versions(self) -> dict:
        """Compare all strategy versions without changing history."""
        versions = sorted(self.records.keys())
        comparison = []
        for version in versions:
            r = self.records[version]
            comparison.append({
                "version": version,
                "trades": r.total_trades,
                "win_rate": r.win_rate,
                "profit_factor": r.profit_factor,
                "expectancy": r.expectancy,
                "sharpe": r.sharpe,
                "max_drawdown": r.max_drawdown,
            })
        return comparison
    
    def print_comparison(self):
        """Print comparison table - history is NEVER changed."""
        print("=" * 75)
        print("  STRATEGY VERSION COMPARISON (Immutable Records)")
        print("=" * 75)
        print(f"\n  {'Version':<10} {'Trades':>8} {'WR':>6} {'PF':>6} {'Exp':>8} {'Sharpe':>7} {'MaxDD':>7}")
        print(f"  {'-'*60}")
        
        for record in sorted(self.records.values(), key=lambda r: r.strategy_version):
            print(f"  {record.strategy_version:<10} {record.total_trades:>8} "
                  f"{record.win_rate:>5.1f}% {record.profit_factor:>6.2f} "
                  f"{record.expectancy:>8.3f} {record.sharpe:>7.2f} "
                  f"{record.max_drawdown:>6.1f}%")
        print(f"  {'='*60}")


if __name__ == "__main__":
    rp = ResearchPlatform()
    
    # Register V3.0 (historical)
    rp.register_strategy(ResearchRecord(
        strategy_version="V3.0",
        dataset="EURUSD 2019-2024",
        train_period="2019-2022",
        validation_period="2023",
        oos_period="2024",
        total_trades=160,
        win_rate=26.3,
        profit_factor=0.65,
        expectancy=-13.41,
        sharpe=-0.85,
        sortino=-1.2,
        max_drawdown=95.0,
        turnover=0.0,
        slippage_sensitivity=0.5,
    ))
    
    # Register V3.1 (current - no data yet)
    rp.register_strategy(ResearchRecord(
        strategy_version="V3.1",
        dataset="EURUSD 2024-2026",
        train_period="2024-2025",
        validation_period="2025",
        oos_period="2026",
        total_trades=0,
        win_rate=0.0,
        profit_factor=0.0,
        expectancy=0.0,
        sharpe=0.0,
        sortino=0.0,
        max_drawdown=0.0,
        turnover=0.0,
        slippage_sensitivity=0.0,
    ))
    
    # Try to change V3.0 (should FAIL - immutable)
    print(f"\n  Attempting to modify V3.0:")
    result = rp.register_strategy(ResearchRecord(
        strategy_version="V3.0",  # DUPLICATE!
        dataset="CHANGED",
        train_period="CHANGED",
        validation_period="CHANGED",
        oos_period="CHANGED",
        total_trades=999,
        win_rate=99.0,
        profit_factor=99.0,
        expectancy=99.0,
        sharpe=99.0,
        sortino=99.0,
        max_drawdown=1.0,
        turnover=1.0,
        slippage_sensitivity=1.0,
    ))
    print(f"  Result: {'ALLOWED (WRONG!)' if result else 'REJECTED (correct - immutable)'}")
    
    # Show comparison
    rp.print_comparison()
    
    # The advisor's required pipeline
    print(f"\n  RESEARCH PIPELINE:")
    pipeline = ["Hypothesis", "Backtest", "Walk-forward", "Out-of-sample", 
                "Paper", "Small live", "Statistical validation", "Production"]
    for i, phase in enumerate(pipeline, 1):
        current = "CURRENT" if i <= 1 else "FUTURE"
        print(f"    {i}. {phase} [{current}]")
