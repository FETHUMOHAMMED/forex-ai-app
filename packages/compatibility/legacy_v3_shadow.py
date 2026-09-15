"""Shadow-only adapters for the characterized legacy V3 implementation.

This module intentionally contains no trading rules.  Each adapter delegates
to an injected legacy object and refuses dependencies that are not explicitly
marked ``shadow_only``.  It is therefore suitable for parity tests and
offline probes, but it is not a production composition root.
"""

from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import Any

from fastapi import HTTPException
from starlette.responses import JSONResponse


class ShadowModeViolation(RuntimeError):
    """Raised when a shadow adapter is given an unapproved dependency."""


def _require_shadow_only(value: Any, label: str) -> None:
    if not getattr(value, "shadow_only", False):
        raise ShadowModeViolation(
            f"{label} must be explicitly marked shadow_only; live dependencies are forbidden"
        )


def _require_legacy_mt5_matches(owner: Any, environment: "ShadowEnvironment") -> None:
    """Prevent legacy modules with a different MT5 global from being called."""

    module = sys.modules.get(owner.__class__.__module__)
    legacy_mt5 = getattr(module, "mt5", None) if module is not None else None
    if legacy_mt5 is not None and legacy_mt5 is not environment.mt5:
        raise ShadowModeViolation(
            "legacy MT5 module does not match the explicitly supplied shadow gateway"
        )


@dataclass(frozen=True)
class ShadowEnvironment:
    """The only environment a Phase 3 adapter may accept."""

    mt5: Any
    http: Any

    def __post_init__(self) -> None:
        _require_shadow_only(self.mt5, "MT5 gateway")
        _require_shadow_only(self.http, "HTTP client")


class ShadowSignalAdapter:
    """Delegate signal calls to a marked, isolated legacy signal producer."""

    def __init__(self, legacy_signal_producer: Any):
        _require_shadow_only(legacy_signal_producer, "legacy signal producer")
        self._legacy = legacy_signal_producer

    def get_real_signal(self, pair: str) -> Any:
        return self._legacy.get_real_signal(pair)

    def get_signal(self, pair: str) -> Any:
        return self._legacy.get_signal(pair)


class ShadowSignalSerializationAdapter:
    """Wrap the legacy signal endpoint as an offline JSON HTTP response."""

    def __init__(self, legacy_endpoint: Any):
        _require_shadow_only(legacy_endpoint, "legacy signal endpoint")
        self._legacy = legacy_endpoint

    async def get_pair_signal(self, pair: str) -> JSONResponse:
        try:
            content = await self._legacy(pair)
            return JSONResponse(content=content, status_code=200)
        except HTTPException as exc:
            return JSONResponse(
                content={"detail": exc.detail},
                status_code=exc.status_code,
                headers=exc.headers,
            )


class ShadowDecisionAdapter:
    """Delegate existing AutoTrader decision/filter helpers unchanged."""

    def __init__(self, legacy_auto_trader: Any):
        _require_shadow_only(legacy_auto_trader, "legacy auto trader")
        self._legacy = legacy_auto_trader

    def is_in_session(self, pair: str) -> Any:
        return self._legacy.is_in_session(pair)

    def position_exists(self, symbol: str, direction: str, positions: Any) -> Any:
        return self._legacy.position_exists(symbol, direction, positions)

    def has_opposite(self, symbol: str, direction: str, positions: Any) -> Any:
        return self._legacy.has_opposite(symbol, direction, positions)

    def session_confidence_adjustment(self, pair: str) -> Any:
        return self._legacy.session_confidence_adjustment(pair)

    def is_correlated_safe(self, pair: str, signal: str, positions: Any) -> Any:
        return self._legacy.is_correlated_safe(pair, signal, positions)


class ShadowRiskAdapter:
    """Delegate legacy risk/sizing calculations without copying their rules."""

    def __init__(self, legacy_auto_trader: Any):
        _require_shadow_only(legacy_auto_trader, "legacy risk owner")
        self._legacy = legacy_auto_trader

    def calc_position_size(
        self, account: Any, pair: str, entry: float, stop_loss: float, risk_pct: float
    ) -> Any:
        return self._legacy.calc_position_size(account, pair, entry, stop_loss, risk_pct)


class ShadowBrokerAdapter:
    """Delegate broker requests only when an isolated shadow environment is used."""

    def __init__(self, legacy_broker: Any, environment: ShadowEnvironment):
        _require_shadow_only(legacy_broker, "legacy broker")
        _require_legacy_mt5_matches(legacy_broker, environment)
        self._legacy = legacy_broker
        self._environment = environment

    def place_market_order(
        self,
        symbol: str,
        order_type: str,
        entry: float,
        sl: float,
        tp: float,
        confidence: float,
        volume: float = 0.01,
    ) -> Any:
        return self._legacy.place_market_order(
            symbol, order_type, entry, sl, tp, confidence, volume=volume
        )


class ShadowPersistenceAdapter:
    """Delegate persistence calls to an explicitly isolated recorder/logger."""

    def __init__(self, shadow_recorder: Any):
        _require_shadow_only(shadow_recorder, "persistence recorder")
        self._legacy = shadow_recorder

    def log_trade_entry(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.log_trade_entry(*args, **kwargs)

    def log_trade_exit(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.log_trade_exit(*args, **kwargs)


class ShadowExecutionAdapter:
    """Delegate the legacy account loop only with shadow-marked dependencies."""

    def __init__(self, legacy_auto_trader: Any, environment: ShadowEnvironment):
        _require_shadow_only(legacy_auto_trader, "legacy execution owner")
        _require_legacy_mt5_matches(legacy_auto_trader, environment)
        self._legacy = legacy_auto_trader
        self._environment = environment

    def manage_account(self, account: Any) -> Any:
        _require_shadow_only(account, "shadow account")
        _require_shadow_only(getattr(account, "broker", None), "account broker")
        return self._legacy.manage_account(account)


class ShadowPositionManagementAdapter:
    """Delegate legacy trailing-stop and time-exit behavior in shadow mode."""

    def __init__(self, legacy_auto_trader: Any, environment: ShadowEnvironment):
        _require_shadow_only(legacy_auto_trader, "legacy position manager")
        _require_legacy_mt5_matches(legacy_auto_trader, environment)
        self._legacy = legacy_auto_trader

    def apply_atr_trailing_stop(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.apply_atr_trailing_stop(*args, **kwargs)

    def apply_time_exit(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.apply_time_exit(*args, **kwargs)
