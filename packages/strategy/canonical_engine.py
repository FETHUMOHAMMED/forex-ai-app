"""CANONICAL Strategy Engine - THE ONLY strategy implementation.
BACKTEST replays it. PAPER uses it. LIVE uses it.

Consolidates what was previously scattered across:
  - strategy.py, smc_decision.py, ict_decision.py
  - smart_trade_plan.py, RealAITrader class
  - adaptive_decision_engine.py, trade_decision_engine.py
  - backtest_engine.py, multi_backtest.py
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum

from packages.strategy.feature_contract import (
    build_features, MarketData, FeatureVector, FEATURE_COLUMNS
)
from packages.domain.models import Signal, SignalDirection
from packages.risk.hard_position_size import calculate_hard_position_size, HardPositionSize
from packages.risk.order_boundary import enforce_order_boundary, RiskGate, RiskGateResult
from packages.domain.errors import (
    TradeRejectionError, MissingRegimeError, StaleSignalError,
    RiskViolationError, LotSizeError, require_regime, require_confidence
)


class EngineMode(str, Enum):
    BACKTEST = "BACKTEST"     # Historical replay
    PAPER = "PAPER"           # Simulated live
    LIVE = "LIVE"             # Real money


@dataclass
class StrategyResult:
    """Complete result from the canonical strategy engine"""
    signal: Optional[Signal]
    position_size: Optional[HardPositionSize]
    risk_gate: Optional[RiskGate]
    rejection_reason: Optional[str]
    mode: EngineMode
    timestamp_utc: str


class CanonicalStrategyEngine:
    """
    THE one and only strategy engine.
    
    Usage:
        engine = CanonicalStrategyEngine(mode=EngineMode.LIVE)
        result = engine.process(market_data, account_state)
        
        if result.risk_gate and result.risk_gate.is_approved:
            # Place order
        else:
            # Trade rejected: result.rejection_reason
    """
    
    def __init__(self, mode: EngineMode = EngineMode.LIVE,
                 model=None,  # XGBoost model
                 account_id: int = REDACTED_LIVE_ACCOUNT,
                 account_name: str = "Live_Micro",
                 risk_percent: float = 0.0005,
                 max_daily_trades: int = 5):
        self.mode = mode
        self.model = model
        self.account_id = account_id
        self.account_name = account_name
        self.risk_percent = risk_percent
        self.max_daily_trades = max_daily_trades
    
    def process(self, market_data: MarketData,
                account_balance: float,
                account_equity: float,
                account_free_margin: float,
                trades_today: int = 0,
                daily_pnl: float = 0,
                open_positions: int = 0) -> StrategyResult:
        """
        CANONICAL process method - the ONLY path from market data to trade decision.
        
        Backtest calls this. Paper trading calls this. Live trading calls this.
        """
        
        # STEP 1: Build features (canonical - same for all modes)
        try:
            features = build_features(market_data)
        except ValueError as e:
            return StrategyResult(None, None, None, f"Feature error: {e}", self.mode,
                                 datetime.now(timezone.utc).isoformat())
        
        # STEP 2: Model prediction (canonical - same model for all modes)
        if self.model:
            prediction = self.model.predict(features.to_array().reshape(1, -1))[0]
            confidence = float(prediction)
            direction = SignalDirection.SELL if prediction < 0.5 else SignalDirection.BUY
        else:
            # No model loaded - use default
            confidence = 0.0
            direction = SignalDirection.SELL
        
        # STEP 3: Validate metadata (fail-fast)
        try:
            regime = require_regime(
                "volatile" if features.values.get("regime_volatile", 0) > 0.5 else "ranging",
                market_data.symbol
            )
            require_confidence(confidence, market_data.symbol, min_conf=0.55)
        except TradeRejectionError as e:
            return StrategyResult(None, None, None, str(e), self.mode,
                                 datetime.now(timezone.utc).isoformat())
        
        # STEP 4: Create signal
        signal = Signal(
            signal_id=f"CANONICAL_{market_data.symbol}_{datetime.now(timezone.utc).timestamp()}",
            symbol=market_data.symbol,
            direction=direction,
            confidence=confidence,
            entry_price=market_data.close,
            stop_loss=market_data.close * 1.0015 if direction == SignalDirection.SELL else market_data.close * 0.9985,
            take_profit=market_data.close * 0.996 if direction == SignalDirection.SELL else market_data.close * 1.004,
            regime=regime,
            institutional_bias="BREAKOUT" if features.values.get("regime_breakout", 0) > 0.5 else "NEUTRAL",
            institutional_score=80.0,
            dealer_pressure="NEUTRAL",
            liquidity_state="NO_EVENT",
            continuation_prob=0.5,
            timestamp_utc=datetime.now(timezone.utc)
        )
        
        # STEP 5: Position sizing (canonical - same formula for all modes)
        position = calculate_hard_position_size(
            equity=account_balance,
            risk_percent=self.risk_percent,
            contract_size=100000, tick_value=1.0, tick_size=0.00001, point=0.00001,
            volume_min=0.01, volume_max=200, volume_step=0.01,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
        )
        
        # STEP 6: Risk gate (canonical - 8 checks for all modes)
        risk_gate = enforce_order_boundary(
            account_balance=account_balance,
            account_equity=account_equity,
            account_free_margin=account_free_margin,
            trades_today=trades_today,
            max_daily_trades=self.max_daily_trades,
            daily_pnl=daily_pnl,
            max_daily_loss_pct=0.05,
            open_positions_count=open_positions,
            max_open_positions=3,
            total_portfolio_risk_pct=0.0,
            max_portfolio_risk_pct=0.03,
            symbol=market_data.symbol,
            volume=position.final_volume,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            symbol_volume_min=0.01, symbol_volume_max=200, symbol_volume_step=0.01,
            symbol_tick_value=1.0, symbol_tick_size=0.00001,
            symbol_point=0.00001, symbol_contract_size=100000,
            max_risk_pct_per_trade=self.risk_percent,
        )
        
        rejection = None if risk_gate.is_approved else risk_gate.reason
        
        return StrategyResult(
            signal=signal,
            position_size=position,
            risk_gate=risk_gate,
            rejection_reason=rejection,
            mode=self.mode,
            timestamp_utc=datetime.now(timezone.utc).isoformat()
        )


# ============================================================================
# DEPRECATION NOTICE - These files are REPLACED by canonical_engine.py
# ============================================================================

DEPRECATED_FILES = """
The following files are DEPRECATED and should be migrated to use CanonicalStrategyEngine:

  ai-service/strategy.py              ? packages/strategy/canonical_engine.py
  institutional/smc_decision.py       ? canonical_engine.py (build_features handles ICT/SMC)
  institutional/ict_decision.py       ? canonical_engine.py (build_features handles ICT/SMC)
  institutional/smart_trade_plan.py   ? canonical_engine.py (TradeIntent + RiskGate)
  ai-service/real_ai_service.py::RealAITrader ? canonical_engine.py (CanonicalStrategyEngine)
  institutional/adaptive_decision_engine.py   ? canonical_engine.py
  institutional/trade_decision_engine.py      ? canonical_engine.py
  backtest/backtest_engine.py         ? canonical_engine.py (mode=BACKTEST)
  backtest/multi_backtest.py          ? canonical_engine.py (mode=BACKTEST)

Migration path:
  1. Import CanonicalStrategyEngine
  2. Set mode=BACKTEST for backtesting
  3. Set mode=PAPER for paper trading
  4. Set mode=LIVE for live trading
  5. All three use the SAME build_features() + process() path
"""
