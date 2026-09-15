"""Offline characterization of auto_trader_exness -> MT5Broker."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import mock_open, patch

from legacy_v3_fixtures import cache_signal, load_legacy_modules


class LegacyV3ExecutionCharacterization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _signal, _daemon, cls.broker_module, cls.execution, cls.mt5 = load_legacy_modules()

    def setUp(self):
        self.mt5.requests.clear()
        self.mt5.order_results.clear()
        self.mt5.logged_in = REDACTED_LIVE_ACCOUNT
        self.mt5.account.login = REDACTED_LIVE_ACCOUNT
        self.mt5.account.margin_free = 10_000.0
        self.mt5.tick = SimpleNamespace(ask=1.10007, bid=1.09997, time=2_000_000_000)
        self.mt5.info = SimpleNamespace(
            point=0.00001, digits=5, filling_mode=1, trade_mode=1,
            trade_tick_value=1.0, trade_tick_size=0.00001,
        )

    def test_buy_submission_is_pending_and_omits_initial_sl_tp(self):
        broker = self.broker_module.MT5Broker(account=REDACTED_LIVE_ACCOUNT)
        broker.connected = True
        result = broker.place_market_order(
            "EURUSDm", "BUY", 1.1, 1.0985, 1.104, 0.83, volume=0.12
        )

        self.assertEqual(result, {"ticket": 123456})
        request = self.mt5.requests[0]
        self.assertEqual(request["action"], self.mt5.TRADE_ACTION_PENDING)
        self.assertEqual(request["type"], self.mt5.ORDER_TYPE_BUY_LIMIT)
        self.assertEqual(request["price"], 1.10007)
        self.assertEqual(request["volume"], 0.12)
        self.assertEqual(request["deviation"], 30)
        self.assertEqual(request["magic"], 234000)
        self.assertEqual(request["comment"], "AI_trade_conf0.83")
        self.assertEqual(request["type_time"], self.mt5.ORDER_TIME_GTC)
        self.assertEqual(request["type_filling"], self.mt5.ORDER_FILLING_FOK)
        self.assertNotIn("sl", request)
        self.assertNotIn("tp", request)
        self.assertNotIn("expiration", request)

    def test_sell_submission_is_pending_and_uses_bid_price(self):
        broker = self.broker_module.MT5Broker(account=REDACTED_LIVE_ACCOUNT)
        broker.connected = True
        broker.place_market_order("EURUSDm", "SELL", 1.1, 1.1015, 1.096, 0.83)

        request = self.mt5.requests[0]
        self.assertEqual(request["type"], self.mt5.ORDER_TYPE_SELL_LIMIT)
        self.assertEqual(request["price"], 1.09997)
        self.assertNotIn("sl", request)
        self.assertNotIn("tp", request)

    def test_transient_error_retries_and_permanent_no_money_stops(self):
        broker = self.broker_module.MT5Broker(account=REDACTED_LIVE_ACCOUNT)
        broker.connected = True
        self.mt5.order_results = [
            SimpleNamespace(retcode=self.mt5.TRADE_RETCODE_REQUOTE, comment="requote", order=0),
            SimpleNamespace(retcode=self.mt5.TRADE_RETCODE_DONE, comment="done", order=123),
        ]
        with patch.object(self.broker_module.time, "sleep", lambda _seconds: None):
            self.assertEqual(
                broker.place_market_order("EURUSDm", "BUY", 1.1, 1.098, 1.104, 0.8),
                {"ticket": 123},
            )
        self.assertEqual(len(self.mt5.requests), 2)

        self.mt5.requests.clear()
        self.mt5.order_results = [
            SimpleNamespace(retcode=self.mt5.TRADE_RETCODE_NO_MONEY, comment="no money", order=0)
        ]
        with patch.object(self.broker_module.time, "sleep", lambda _seconds: None):
            self.assertIsNone(
                broker.place_market_order("EURUSDm", "BUY", 1.1, 1.098, 1.104, 0.8)
            )
        self.assertEqual(len(self.mt5.requests), 1)

    def test_margin_failure_is_fail_closed_before_order_send(self):
        broker = self.broker_module.MT5Broker(account=REDACTED_LIVE_ACCOUNT)
        broker.connected = True
        self.mt5.account.margin_free = 1.0
        self.assertIsNone(
            broker.place_market_order("EURUSDm", "BUY", 1.1, 1.098, 1.104, 0.8)
        )
        self.assertEqual(self.mt5.requests, [])

    def test_trade_logger_entry_and_exit_payload(self):
        from risk.trade_logger import TradeLogger

        logger = TradeLogger(db_path=":memory:")
        signal = cache_signal()
        ticket = logger.log_trade_entry(
            signal, volume=0.12, ticket=987, regime="volatile", account="Live_Micro"
        )
        self.assertEqual(ticket, 1)
        logger.log_trade_exit(
            ticket=987,
            exit_price=1.15,
            exit_time=datetime(2026, 8, 13, tzinfo=timezone.utc),
            pnl=2.5,
            reason="closed",
        )
        row = logger.conn.execute(
            "SELECT pair, signal, confidence, entry, stop_loss, take_profit, volume, ticket, regime, account, result, reason FROM trades WHERE ticket=987"
        ).fetchone()
        self.assertEqual(row, (
            "EURUSD", "BUY", 0.83, 1.15123, 1.15299, 1.14842,
            0.12, 987, "volatile", "Live_Micro", "WIN", "closed"
        ))
        logger.conn.close()

    def test_position_sizing_prefers_tick_value_and_rounds(self):
        trader = self.execution.AutoTrader.__new__(self.execution.AutoTrader)
        acc = SimpleNamespace(name="Live_Micro", broker=SimpleNamespace(get_balance=lambda: 10_000.0))
        self.assertEqual(trader.calc_position_size(acc, "EURUSD", 1.1, 1.0985, 0.01), 0.67)

    def test_duplicate_and_opposite_position_helpers(self):
        trader = self.execution.AutoTrader.__new__(self.execution.AutoTrader)
        positions = [{"symbol": "EURUSDm", "type": 0}, {"symbol": "GBPUSD", "type": 1}]
        self.assertTrue(trader.position_exists("EURUSD", "BUY", positions))
        self.assertFalse(trader.position_exists("EURUSD", "SELL", positions))
        self.assertTrue(trader.has_opposite("EURUSDm", "SELL", positions))

    def test_trailing_stop_submits_sltp_only_after_one_atr_profit(self):
        trader = self.execution.AutoTrader.__new__(self.execution.AutoTrader)
        acc = SimpleNamespace(broker=SimpleNamespace(connected=True))
        position = {"ticket": 55, "sl": 1.0990, "tp": 1.1100}
        self.mt5.tick = SimpleNamespace(bid=1.1020, ask=1.1022, time=2_000_000_000)
        trader.apply_atr_trailing_stop(acc, "EURUSDm", 0.001, "BUY", 1.1000, position)
        self.assertEqual(self.mt5.requests, [{
            "action": self.mt5.TRADE_ACTION_SLTP,
            "position": 55, "sl": 1.1000, "tp": 1.1100,
        }])

    def test_time_exit_submits_pending_close_for_old_losing_position(self):
        trader = self.execution.AutoTrader.__new__(self.execution.AutoTrader)
        acc = SimpleNamespace(broker=SimpleNamespace(connected=True))
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).timestamp()
        position = {
            "ticket": 56, "symbol": "EURUSDm", "type": 0, "volume": 0.1,
            "profit": -1.0, "time": old_time,
        }
        self.mt5.tick = SimpleNamespace(bid=1.1020, ask=1.1022, time=2_000_000_000)
        trader.apply_time_exit(acc, "EURUSDm", position, max_hours=24)
        request = self.mt5.requests[0]
        self.assertEqual(request["action"], self.mt5.TRADE_ACTION_PENDING)
        self.assertEqual(request["position"], 56)
        self.assertEqual(request["type"], self.mt5.ORDER_TYPE_SELL)
        self.assertEqual(request["comment"], "time_exit_loss")

    def test_manage_account_accepts_signal_and_logs_boundary_payload(self):
        trader, acc, broker = self._make_trader_and_account()
        response = _Response(200, {"signal": cache_signal(confidence=0.80)})
        with patch.object(self.execution.requests, "get", return_value=response), \
             patch.object(self.execution.time, "sleep", lambda _seconds: None):
            trader.manage_account(acc)

        self.assertEqual(broker.place_calls[0][0], "EURUSDm")
        self.assertEqual(broker.place_calls[0][1], "BUY")
        self.assertEqual(broker.place_calls[0][5], 0.80)
        self.assertEqual(broker.place_calls[0][6], 0.80)
        self.assertEqual(acc.logged[0]["ticket"], 123456)
        self.assertEqual(acc.logged[0]["regime"], "volatile")

    def test_manage_account_session_and_confidence_gates_reject(self):
        for mode in ("session", "confidence"):
            trader, acc, broker = self._make_trader_and_account()
            if mode == "session":
                trader.is_in_session = lambda pair: False
            else:
                acc.min_confidence = 0.90
            response = _Response(200, {"signal": cache_signal(confidence=0.80)})
            with patch.object(self.execution.requests, "get", return_value=response), \
                 patch.object(self.execution.time, "sleep", lambda _seconds: None):
                trader.manage_account(acc)
            self.assertEqual(broker.place_calls, [], mode)

    def test_manage_account_regime_duplicate_atr_spread_and_quality_reject(self):
        cases = [
            (cache_signal(direction="SELL", confidence=0.80), "regime"),
            (cache_signal(confidence=0.80), "duplicate"),
            (cache_signal(confidence=0.80), "opposite"),
            (cache_signal(direction="SELL", confidence=0.80), "exposure"),
            (cache_signal(confidence=0.80), "correlation"),
            (dict(cache_signal(confidence=0.80), atr=0.00001), "atr"),
            (cache_signal(confidence=0.80), "spread"),
            (dict(cache_signal(confidence=0.51), strength="WEAK"), "quality"),
        ]
        for signal, mode in cases:
            self.mt5.tick = SimpleNamespace(ask=1.10007, bid=1.09997, time=2_000_000_000)
            trader, acc, broker = self._make_trader_and_account()
            if mode == "regime":
                signal["regime"] = "BULLISH"
            elif mode == "duplicate":
                broker.positions = [{"symbol": "EURUSDm", "type": 0, "ticket": 1, "volume": 0.1, "profit": 0, "open_price": 1.1, "sl": 1.09, "tp": 1.11, "time": 2_000_000_000}]
            elif mode == "opposite":
                broker.positions = [{"symbol": "EURUSDm", "type": 1, "ticket": 1, "volume": 0.1, "profit": 0, "open_price": 1.1, "sl": 1.11, "tp": 1.09, "time": 2_000_000_000}]
            elif mode == "exposure":
                broker.positions = [
                    {"symbol": "GBPUSD", "type": 1, "ticket": 2, "time": 2_000_000_000},
                    {"symbol": "AUDUSD", "type": 1, "ticket": 3, "time": 2_000_000_000},
                ]
            elif mode == "correlation":
                broker.positions = [
                    {"symbol": "GBPUSD", "type": 0, "ticket": 2, "time": 2_000_000_000},
                    {"symbol": "AUDUSD", "type": 0, "ticket": 3, "time": 2_000_000_000},
                    {"symbol": "NZDUSD", "type": 0, "ticket": 4, "time": 2_000_000_000},
                ]
            elif mode == "spread":
                self.mt5.tick = SimpleNamespace(ask=1.1010, bid=1.1000, time=2_000_000_000)
            elif mode == "quality":
                acc.min_confidence = 0.50
            response = _Response(200, {"signal": signal})
            with patch.object(self.execution.requests, "get", return_value=response), \
                 patch.object(self.execution.time, "sleep", lambda _seconds: None):
                trader.manage_account(acc)
            if mode == "opposite":
                # Observed legacy behavior: EURUSDm does not match the
                # unsuffixed EURUSD in has_opposite(), so the order proceeds.
                self.assertEqual(broker.place_calls[0][0], "EURUSDm")
            else:
                self.assertEqual(broker.place_calls, [], mode)

    def test_manage_account_account_level_gates_reject_before_signal_fetch(self):
        cases = ("daily_loss", "drawdown", "daily_trades", "news", "portfolio_risk")
        for mode in cases:
            trader, acc, broker = self._make_trader_and_account()
            if mode == "daily_loss":
                broker.equity = 9_000.0
            elif mode == "drawdown":
                broker.equity = 9_000.0
                acc.daily_peak_balance = 10_000.0
            elif mode == "daily_trades":
                acc.daily_trades = acc.max_daily_trades
            elif mode == "news":
                trader.news_filter = SimpleNamespace(is_high_impact_nearby=lambda pair: True)
            elif mode == "portfolio_risk":
                broker.positions = [{
                    "symbol": "GBPUSD", "type": 0, "ticket": 2, "volume": 0.30,
                    "profit": 0, "open_price": 1.1, "sl": 1.09, "tp": 1.11,
                    "time": datetime.now(timezone.utc).timestamp(),
                }]
            response = _Response(200, {"signal": cache_signal(confidence=0.80)})
            with patch.object(self.execution.requests, "get", return_value=response) as http_get, \
                 patch.object(self.execution.time, "sleep", lambda _seconds: None):
                trader.manage_account(acc)
            self.assertEqual(broker.place_calls, [], mode)
            if mode in ("daily_loss", "drawdown", "daily_trades", "news"):
                http_get.assert_not_called()

    def test_runtime_config_is_optional_and_dynamically_read(self):
        trader = self.execution.AutoTrader.__new__(self.execution.AutoTrader)
        trader.accounts = [SimpleNamespace(name="Demo2"), SimpleNamespace(name="Live_Micro")]
        with patch.object(self.execution.os.path, "exists", return_value=False):
            self.assertEqual(
                trader.get_runtime_config(),
                {"active_accounts": ["Demo2", "Live_Micro"]},
            )

        with patch.object(self.execution.os.path, "exists", return_value=True), \
             patch("builtins.open", mock_open(read_data='{"active_accounts": ["Live_Micro"]}')):
            self.assertEqual(
                trader.get_runtime_config(),
                {"active_accounts": ["Live_Micro"]},
            )

    def _make_trader_and_account(self):
        trader = self.execution.AutoTrader.__new__(self.execution.AutoTrader)
        trader._paused = False
        trader.daily_summary_sent_today = True
        trader._last_reset_day = datetime.now(timezone.utc).date()
        trader._news_cache = {}
        trader.news_filter = SimpleNamespace(is_high_impact_nearby=lambda pair: False)
        trader.notifier = None
        trader.slack_notifier = None
        trader.rejection_counts = {key: 0 for key in (
            "confidence", "session", "news", "correlation", "atr", "duplicate",
            "opposite", "trending_skip", "max_trades", "no_ensemble", "total_signals",
            "accepted", "volatile_skip", "ranging_skip", "spread", "no_signal",
        )}
        trader.is_forex_market_open = lambda: True
        trader.is_in_session = lambda pair: True
        trader.session_confidence_adjustment = lambda pair: 0.0
        trader.update_risk_allocation = lambda acc: None
        trader.update_pair_allocation = lambda acc: None
        trader.check_drift = lambda acc: None
        trader.atr_min_non_jpy = 0.0006
        trader.atr_max_non_jpy = 0.002
        trader.atr_min_jpy = 0.08
        trader.atr_max_jpy = 0.3

        broker = _BrokerDouble()
        acc = SimpleNamespace(
            name="Live_Micro", enabled=True, _paused=False, broker=broker,
            pairs=["EURUSD"], min_confidence=0.75, risk_percent=0.01,
            max_daily_trades=4, max_daily_loss_percent=0.05,
            trail_drawdown_percent=0.05, starting_balance=10_000.0,
            daily_peak_balance=10_000.0, daily_trades=0, daily_pnl=0.0,
            today=datetime.now(timezone.utc).date(), equity_history=[], failed_pairs={},
            last_trade_time={}, previous_tickets=set(), _cooldown_cleared=False,
            _original_risk=0.01,
            hedge=self.execution.HedgeState(), streak_enabled=False,
            loss_streak=0, streak_threshold=3, streak_risk_mult=0.5,
            regime_risk_multipliers={}, pair_risk_weights={},
            logged=[], reconnect=lambda: None,
        )
        acc.logger = SimpleNamespace(
            log_trade_entry=lambda signal, volume=None, ticket=None, regime=None: acc.logged.append({
                "signal": signal, "volume": volume, "ticket": ticket, "regime": regime
            }),
            log_trade_exit=lambda **kwargs: None,
        )
        return trader, acc, broker


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class _BrokerDouble:
    def __init__(self):
        self.connected = True
        self.account = REDACTED_LIVE_ACCOUNT
        self.password = ""
        self.server = "Exness-MT5Real10"
        self.positions = []
        self.place_calls = []
        self.equity = 10_000.0

    def reconnect(self):
        return True

    def get_balance(self):
        return 10_000.0

    def get_equity(self):
        return self.equity

    def get_positions(self):
        return list(self.positions)

    def place_market_order(self, *args, **kwargs):
        self.place_calls.append((*args, kwargs.get("volume")))
        return {"ticket": 123456}


if __name__ == "__main__":
    unittest.main()
