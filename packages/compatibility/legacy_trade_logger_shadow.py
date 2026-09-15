"""Shadow-only adapter for the characterized legacy TradeLogger."""

from __future__ import annotations

from typing import Any

from .legacy_v3_shadow import ShadowModeViolation, _require_shadow_only


def _require_memory_database(logger: Any) -> None:
    connection = getattr(logger, "conn", None)
    if connection is None:
        raise ShadowModeViolation("legacy TradeLogger must expose an isolated SQLite connection")
    try:
        databases = connection.execute("PRAGMA database_list").fetchall()
    except Exception as exc:
        raise ShadowModeViolation("unable to verify the TradeLogger database boundary") from exc
    if not databases or any(row[2] for row in databases):
        raise ShadowModeViolation("shadow TradeLogger adapters accept only :memory: SQLite")


class ShadowTradeLoggerAdapter:
    """Delegate legacy persistence calls without adding schema or data rules."""

    def __init__(self, legacy_logger: Any):
        _require_shadow_only(legacy_logger, "legacy TradeLogger")
        _require_memory_database(legacy_logger)
        self._legacy = legacy_logger

    def log_trade_entry(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.log_trade_entry(*args, **kwargs)

    def log_trade_exit(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.log_trade_exit(*args, **kwargs)

    def get_recent_pnls(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.get_recent_pnls(*args, **kwargs)

    def get_recent_trade_stats(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.get_recent_trade_stats(*args, **kwargs)

    def get_regime_performance(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.get_regime_performance(*args, **kwargs)

    def get_pair_performance(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.get_pair_performance(*args, **kwargs)

    def get_daily_stats(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.get_daily_stats(*args, **kwargs)

    def get_performance_stats(self, *args: Any, **kwargs: Any) -> Any:
        return self._legacy.get_performance_stats(*args, **kwargs)
