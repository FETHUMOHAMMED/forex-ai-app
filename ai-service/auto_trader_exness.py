"""
AUTOMATED TRADING BOT – EXNESS MT5
Multi‑account / Prop‑Firm support. Each account has its own settings.
Includes: dynamic position sizing, daily drawdown, trailing drawdown,
trailing stop (adaptive/ATR), break‑even & partial close, Telegram & Slack alerts,
daily summary, equity chart, correlation filter, news filter, session filter,
weekly model retraining, remote kill switch, auto‑reconnect on MT5 loss,
watchdog compatibility, Telegram account switching, AUTOMATIC RISK REDUCTION
after losing streaks, and Intelligent Hedging Mode.
(Fixed: /status now logs into each account before querying; duplicate pair check added)
Includes all risk management, filters, notifications, and safety guards,
REGIME‑BASED PARAMETER SWITCHING (trending, ranging, volatile).
"""

from asyncio.log import logger
from multiprocessing.util import info
import time, sys, os, json, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import timedelta
from datetime import datetime, timezone
import pandas as pd
import MetaTrader5 as mt5
import numpy as np

from analytics.monte_carlo import monte_carlo
from broker_exness import MT5Broker
from risk.trade_logger import TradeLogger
from notify.telegram_notifier import TelegramNotifier
from notify.slack_notifier import SlackNotifier
from analytics.chart_generator import ChartGenerator
from risk.news_filter import NewsFilter
from analytics.report_generator import ReportGenerator
from risk.regime_detector import detect_regime
from dotenv import load_dotenv
import joblib
import random

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

# ----------------------------------------------------------------------
# Hedge State helper
# ----------------------------------------------------------------------

class HedgeState:
    def __init__(self, enabled=False, threshold=3, direction='opposite'):
        self.enabled = enabled
        self.threshold = threshold
        self.direction = direction
        self.active = False
        self.losing_streak = 0
        self.last_losing_direction = None
    
    def update(self, trade_result, trade_signal):
        if trade_result == 'LOSS':
            self.losing_streak += 1
            self.last_losing_direction = trade_signal
            if self.enabled and self.losing_streak >= self.threshold:
                self.active = True
        else:
            self.losing_streak = 0
            self.active = False
            self.last_losing_direction = None

    def reset(self):
        self.losing_streak = 0
        self.active = False
        self.last_losing_direction = None

    def allow_signal(self, signal):
        if not self.active or not self.last_losing_direction:
            return True
        if self.direction == 'opposite':
            return signal != self.last_losing_direction
        else:
            return signal == self.last_losing_direction
    
# ----------------------------------------------------------------------
# Account‑specific state (holds its own broker session)
# ----------------------------------------------------------------------
class AccountState:
    def __init__(self, acc_cfg, global_cfg, ai, logger, chart_gen, report_gen):
        self.name = acc_cfg['name']
        self.enabled = acc_cfg.get('enabled', True)
        # If the account is disabled, skip broker setup and mark it as disconnected
        if not self.enabled:
            self.broker = None
            self.pairs = []
            self.starting_balance = 0.0
            self.daily_peak_balance = 0.0
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.today = datetime.now().date()
            self._paused = True
            self.ai = ai
            self.logger = logger
            self.chart_gen = chart_gen
            self.report_gen = report_gen
            self.last_trade_time = {}
            self.failed_pairs = {}
            return
                # ----- Broker factory -----
        broker_name = acc_cfg.get('broker', 'Exness')   # default to Exness for backward compatibility
        if broker_name.lower() in ('exness', 'icmarkets', 'mt5'):
            # All MT5-based brokers use the same MT5Broker class
            from broker_exness import MT5Broker
            self.broker = MT5Broker(
                account=int(acc_cfg['account']),
                password=os.getenv(f"{acc_cfg['name'].upper()}_PASSWORD", acc_cfg.get('password', '')),
                server=acc_cfg['server'],
                auto_connect=False
            )
        else:
            # Future: add support for other broker APIs here
            raise ValueError(f"Unsupported broker: {broker_name}")

        # Connect with retries
        for attempt in range(5):
            if self.broker.connect():
                break
            print(f"⚠️ MT5 not available, retrying in 10 seconds... (attempt {attempt+1}/5)")
            time.sleep(10)
        else:
            print(f"❌ Could not connect to MT5 for account {self.name}")

        self.pairs = acc_cfg.get('pairs', global_cfg.get('pairs', ['EURUSD']))
        self.min_confidence = acc_cfg.get('min_confidence', 0.55)
        self.risk_percent = acc_cfg.get('risk_percent', 1.0) / 100.0
        self.max_daily_trades = acc_cfg.get('max_daily_trades', 8)
        self.max_daily_loss_percent = acc_cfg.get('max_daily_loss_percent', 5.0) / 100.0
        self.trail_atr_mult = acc_cfg.get('trail_atr_mult', 1.0)
        self.trail_drawdown_percent = acc_cfg.get('trail_drawdown_percent', 5.0) / 100.0
        self.break_even_atr_mult = acc_cfg.get('break_even_atr_mult', 1.0)
        self.enable_partial_close = acc_cfg.get('enable_partial_close', False)
        self.partial_close_rr_mult = acc_cfg.get('partial_close_rr_mult', 1.0)
        self.partial_close_fraction = acc_cfg.get('partial_close_fraction', 0.5)
        self.atr_min_non_jpy = acc_cfg.get('atr_min_non_jpy', global_cfg.get('atr_min_non_jpy', 0.0006))
        self.atr_max_non_jpy = acc_cfg.get('atr_max_non_jpy', global_cfg.get('atr_max_non_jpy', 0.002))
        self.atr_min_jpy = acc_cfg.get('atr_min_jpy', global_cfg.get('atr_min_jpy', 0.08))
        self.atr_max_jpy = acc_cfg.get('atr_max_jpy', global_cfg.get('atr_max_jpy', 0.3))
        
        # Streak risk reduction
        self.streak_enabled = acc_cfg.get('loss_streak_reduce_enabled', False)
        self.streak_threshold = acc_cfg.get('loss_streak_threshold', 3)
        self.streak_risk_mult = acc_cfg.get('loss_streak_risk_multiplier', 0.5)
        self.loss_streak = 0
        self.consecutive_losses = 0
        self.consecutive_loss_limit = acc_cfg.get('consecutive_loss_limit', 5)
        self.loss_pause_until = None   # datetime when pause ends
        self._original_risk = self.risk_percent
        self.equity_history = []   # last 20 daily balances

        # Hedge mode
        hedge_cfg = {
            'enabled': acc_cfg.get('hedge_mode_enabled', False),
            'threshold': acc_cfg.get('hedge_mode_threshold', 3),
            'direction': acc_cfg.get('hedge_mode_direction', 'opposite')
        }
        self.hedge = HedgeState(**hedge_cfg)

        # Regime parameters
        self.regime_params = acc_cfg.get('regime_params', {})

        # Daily state
        self.starting_balance = self.broker.get_balance() if self.broker.connected else 0.0
        self.daily_peak_balance = self.starting_balance
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.today = datetime.now().date()
        self._paused = False

        # Helpers
        self.ai = ai
        self.logger = logger
        self.chart_gen = chart_gen
        self.report_gen = report_gen

        # Per‑pair cooldown (last trade time)
        self.last_trade_time = {}
        self.failed_pairs = {}

    def connect(self):
        for attempt in range(5):
            if self.broker.connect():
                return
            print(f"⚠️ MT5 connect retry {attempt+1}/5 for {self.name}")
            time.sleep(10)

    def reconnect(self):
        """Reconnect only when disconnected, or every 30 minutes to refresh the session."""
        now = datetime.now(timezone.utc)
        last = getattr(self, '_last_reconnect', None)
        if not self.broker.connected or (last and (now - last).total_seconds() > 1800):
            self.connect()
            self._last_reconnect = now

    def get_balance(self):
        return self.broker.get_balance()


# ----------------------------------------------------------------------
# Main AutoTrader
# ----------------------------------------------------------------------
class AutoTrader:
    def __init__(self):
        self.ai_service_url = 'http://localhost:8001/signals'
        self.logger = TradeLogger(db_path="trades.db")
        self.chart_gen = ChartGenerator(db_path="trades.db")
        self.report_gen = ReportGenerator(db_path="trades.db")
        
        self.last_allocation_update = None
        self.loop_sleep = CONFIG.get('loop_sleep_seconds', 30)
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.notifier = TelegramNotifier(bot_token, chat_id) if bot_token and chat_id else None
        slack_webhook = os.getenv('SLACK_WEBHOOK_URL', '')
        self.slack_notifier = SlackNotifier(slack_webhook) if slack_webhook else None
        
        self._news_cache = {}          # { pair: (timestamp, result) }
        self.news_filter = NewsFilter(
            blackout_minutes=CONFIG.get('news_filter_blackout_minutes', 30),
            impact_levels=CONFIG.get('news_filter_impact_levels', ['high'])
        )

        # Global filters (overridden by regime params)
        self.atr_min_non_jpy = CONFIG.get('atr_min_non_jpy', 0.0005)
        self.atr_max_non_jpy = CONFIG.get('atr_max_non_jpy', 0.003)
        self.atr_min_jpy = CONFIG.get('atr_min_jpy', 0.05)
        self.atr_max_jpy = CONFIG.get('atr_max_jpy', 0.3)
        self.use_filters = CONFIG.get('use_filters', True)
        self.trailing_stop_type = CONFIG.get('trailing_stop_type', 'adaptive')
        self.adaptive_trail_lookback = CONFIG.get('adaptive_trail_lookback', 20)

        self.session_hours = CONFIG.get('session_hours', {})
        self.correlated_pairs = CONFIG.get('correlated_pairs', {})
        
        # Startup validation – critical files must exist
        if not os.path.exists(CONFIG_PATH):
            print("❌ config.json not found – exiting.")
            sys.exit(1)
        if not os.path.exists('models'):
            print("❌ models folder not found – exiting.")
            sys.exit(1)
        # Also check that at least one account is configured
        accounts_cfg = CONFIG.get('accounts', [])
        if not accounts_cfg:
            print("❌ No accounts found in config.json – exiting.")
            sys.exit(1)

        # Build account states
        accounts_cfg = CONFIG.get('accounts', [])
        if not accounts_cfg:
            # fallback
            accounts_cfg = [{
                'name': 'Default',
                'account': os.getenv('EXNESS_ACCOUNT', ''),
                'password': os.getenv('EXNESS_PASSWORD', ''),
                'server': os.getenv('EXNESS_SERVER', 'Exness-MT5Trial9'),
                'pairs': ['EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','USDCHF','NZDUSD','USDSGD'],
                'min_confidence': 0.55,
                'risk_percent': 1.0,
                'max_daily_trades': 8,
                'max_daily_loss_percent': 5.0,
                'trail_drawdown_percent': 5.0,
                'trail_atr_mult': 1.0,
                'break_even_atr_mult': 1.0,
                'enable_partial_close': True,
                'partial_close_rr_mult': 1.0,
                'partial_close_fraction': 0.5,
                'enabled': True,
                'loss_streak_reduce_enabled': True,
                'loss_streak_threshold': 3,
                'loss_streak_risk_multiplier': 0.5,
                'hedge_mode_enabled': True,
                'hedge_mode_threshold': 3,
                'hedge_mode_direction': 'opposite',
                'regime_params': {}
            }]
            
        self.rejection_counts = {
            'confidence': 0,
            'session': 0,
            'news': 0,
            'correlation': 0,
            'atr': 0,
            'duplicate': 0,
            'opposite': 0,
            'trending_skip': 0,
            'max_trades': 0,
            'no_ensemble': 0,
            'total_signals': 0,
            'accepted': 0,
            'volatile_skip': 0,
            'ranging_skip': 0,
            'spread': 0
        }
        
        self.accounts = []
        for acc_cfg in accounts_cfg:
            state = AccountState(acc_cfg, CONFIG, None, self.logger,
                                 self.chart_gen, self.report_gen)
            # Skip disabled accounts
            if not state.enabled:
                print(f"⏸️ {state.name} is disabled – skipping")
                continue
            # For enabled accounts, broker must exist and be connected
            if state.broker is None or not state.broker.connected:
                print(f"❌ Cannot connect account {state.name} - skipping")
                continue
            self.accounts.append(state)

        if not self.accounts:
            print("❌ No accounts connected. Exiting.")
            sys.exit(1)

        self._paused = False
        self._last_update_id = 0
        self.daily_summary_sent_today = False
        self._last_reset_day = None
        self._last_heartbeat = None
        self.last_status_time = None
        print(f"\n📊 MULTI‑ACCOUNT SETTINGS:")
        for acc in self.accounts:
            print(f"   {acc.name}: {acc.pairs} | Risk {acc.risk_percent:.1%} | "
                  f"Max trades {acc.max_daily_trades} | DD limit {acc.max_daily_loss_percent:.1%} | "
                  f"Trailing DD {acc.trail_drawdown_percent:.1%}")
        print(f"   Telegram: {'✅' if self.notifier else '❌'}")
        print(f"   Slack: {'✅' if self.slack_notifier else '❌'}")
        print(f"   Regime Switching: ✅ trending / ranging / volatile")
        print("=" * 60)
        # Centralized MT5 initialization – only once per process
        if not mt5.initialize():
            print("❌ MT5 failed to initialise")
            sys.exit(1)
        
        # Cache the regime parameters from the Live account (read once)
        self.live_regime_params = {}
        for acc in CONFIG.get('accounts', []):
            if acc.get('name') == 'Live':
                self.live_regime_params = acc.get('regime_params', {})
                break
        
        # Load regime predictor (Phase 2)
        try:
            self.regime_predictor = joblib.load('regime_predictor.joblib')
            self.regime_scaler = joblib.load('regime_predictor_scaler.joblib')
            print("🔮 Regime predictor loaded")
        except Exception as e:
            self.regime_predictor = None
            self.regime_scaler = None
            print(f"⚠️ Regime predictor not available: {e}")
         
         # Drift detection settings
        self.drift_days = CONFIG.get('drift_days', 30)
        self.drift_winrate_threshold = CONFIG.get('drift_winrate_threshold', 55.0)  # percent
        self.drift_critical_threshold = CONFIG.get('drift_critical_threshold', 45.0)
        self.drift_pause_enabled = CONFIG.get('drift_pause_enabled', True)
        self.last_drift_check = None
        
        # Build a symbol map once at startup
        self.symbol_map = {}
        for acc in self.accounts:
            for pair in acc.pairs:
                if pair not in self.symbol_map:
                    actual = self._find_symbol(pair)
                    if actual:
                        self.symbol_map[pair] = actual

    def _find_symbol(self, pair):
        """Find the actual MT5 symbol name for a pair (handles broker suffixes)."""
        candidates = [pair, f"{pair}m", f"{pair}.", f"{pair}pro", f"{pair}.pro"]
        for sym in candidates:
            info = mt5.symbol_info(sym)
            if info is not None:
                mt5.symbol_select(sym, True)
                return sym
        return None
    
    def update_risk_allocation(self, acc):
        """
        Update acc.regime_risk_multipliers based on recent 30‑day profit factor.
        Smooth scaling:
          PF >= 1.3  → 1.0 (full risk)
          PF >= 1.1  → 0.8
          PF >= 1.0  → 0.6
          PF < 1.0   → 0.4
        Regimes with < 10 closed trades keep the default (1.0).
        """
        now = datetime.now(timezone.utc)
        if self.last_allocation_update and (now - self.last_allocation_update).total_seconds() < 3600:
            return
        self.last_allocation_update = now

        perf = self.logger.get_regime_performance(days=30)
        if not perf:
            return   # no data yet

        new_multipliers = {}
        for regime in ['trending', 'ranging', 'volatile']:
            data = perf.get(regime)
            if data and data['trades'] >= 10:
                pf = data['profit_factor']
                if pf >= 1.3:
                    mult = 1.0
                elif pf >= 1.1:
                    mult = 0.8
                elif pf >= 1.0:
                    mult = 0.6
                else:
                    mult = 0.4
                new_multipliers[regime] = mult
            else:
                new_multipliers[regime] = 1.0   # default, no adjustment

        acc.regime_risk_multipliers = new_multipliers

        # Telegram summary (optional, sent at most once per day)
        if self.notifier:
            summary = f"📊 {acc.name} Risk Allocation (30‑day PF):\n"
            for regime, mult in new_multipliers.items():
                if regime in perf and perf[regime]['trades'] >= 10:
                    d = perf[regime]
                    summary += f"{regime.capitalize()}: {d['trades']} trades, PF {d['profit_factor']:.2f} → x{mult}\n"
                else:
                    summary += f"{regime.capitalize()}: insufficient data → x{mult}\n"
            self.notifier.send_message(summary)

    def update_pair_allocation(self, acc):
        """
        Compute per‑pair risk weights based on the last 30 days of closed trades.
        Pairs with fewer than 10 closed trades keep a weight of 1.0 (no change).
        """
        now = datetime.now(timezone.utc)
        if not hasattr(acc, 'pair_risk_weights'):
            acc.pair_risk_weights = {}
        # Only recalculate every hour
        last_update = getattr(acc, '_last_pair_alloc_update', None)
        if last_update and (now - last_update).total_seconds() < 3600:
            return
        acc._last_pair_alloc_update = now

        # Get per‑pair performance (we'll need a new query)
        pair_perf = self.logger.get_pair_performance(days=30)
        if not pair_perf:
            # No data yet – keep existing weights
            if not acc.pair_risk_weights:
                for pair in acc.pairs:
                    acc.pair_risk_weights[pair] = 1.0
            return

        # Update weights
        for pair in acc.pairs:
            data = pair_perf.get(pair)
            if data and data['trades'] >= 10:
                pf = data['profit_factor']
                if pf >= 1.3:
                    weight = 1.0
                elif pf >= 1.1:
                    weight = 0.8
                elif pf >= 1.0:
                    weight = 0.6
                else:
                    weight = 0.0   # disable losing pairs
            else:
                weight = 1.0   # not enough data, keep trading
            acc.pair_risk_weights[pair] = weight

        # Optional Telegram summary
        if self.notifier:
            summary = f"📊 {acc.name} Pair Allocation (30‑day PF):\n"
            for pair, weight in acc.pair_risk_weights.items():
                if pair in pair_perf and pair_perf[pair]['trades'] >= 10:
                    d = pair_perf[pair]
                    summary += f"   {pair}: {d['trades']} trades, PF {d['profit_factor']:.2f} → x{weight}\n"
                else:
                    summary += f"   {pair}: insufficient data → x{weight}\n"
            self.notifier.send_message(summary)
    
    def daily_monte_carlo_check(self):
        """
        Run a Monte Carlo test on the last 100 closed trades.
        Alert if survival rate drops below 90% or median drawdown exceeds -5%.
        """
        # Only run once per day
        now = datetime.now(timezone.utc)
        print(f"[MC DEBUG] Checking Monte Carlo... last check: {getattr(self, '_last_mc_check', 'never')}")
        last_mc = getattr(self, '_last_mc_check', None)
        if last_mc and (now - last_mc).total_seconds() < 86400:  # 24 hours
            return
        self._last_mc_check = now

        # Get recent PnLs but only for current winning pairs
        all_pnls = self.logger.get_recent_pnls(limit=200)
        # Filter to only include pairs we still trade
        winning_pairs = ['USDJPY', 'USDCAD', 'USDCHF', 'EURUSD']
        # This is a simple PnL array so we can't filter by pair here
        # The Monte Carlo will improve as old trades age out
        pnls = all_pnls
        if len(pnls) < 30:
            return   # not enough data

        # Monte Carlo settings (same as standalone script)
        results = monte_carlo(np.array(pnls), num_sims=500)

        alert = False
        msg = "📊 Daily Monte Carlo Check:\n"
        msg += f"Trades sampled: {len(pnls)}\n"
        msg += f"Survival rate: {results['survival_rate']:.1%}\n"
        msg += f"Median final equity: ${results['median_final_equity']:,.2f}\n"
        msg += f"Median max drawdown: {results['median_max_dd']:.1%}\n"
        msg += f"Ruin probability: {results['ruin_probability']:.1%}"

        if results['survival_rate'] < 0.90:
            alert = True
            msg += "\n⚠️ Survival rate below 90%"
        if results['median_max_dd'] < -0.05:   # drawdown worse than -5%
            alert = True
            msg += "\n⚠️ Median drawdown worse than -5%"

        if alert and self.notifier:
            msg = "🚨 Monte Carlo ALERT – Edge may be fading\n" + msg
            self.notifier.send_message(msg)
        elif self.notifier:
            msg = "✅ Monte Carlo OK\n" + msg
            self.notifier.send_message(msg)
    
    def check_drift(self, acc):
        """
        Monitor recent win rate. If below threshold, send warning.
        If below critical threshold, pause account and alert.
        """
        # Run at most once per hour
        now = datetime.now(timezone.utc)
        if self.last_drift_check and (now - self.last_drift_check).total_seconds() < 3600:
            return
        self.last_drift_check = now

        total, wins, wr = self.logger.get_recent_trade_stats(days=self.drift_days, account=acc.name)
        if total < 10:      # not enough data
            return

        if wr < self.drift_critical_threshold and self.drift_pause_enabled:
            acc._paused = True
            msg = (f"🚨 {acc.name} PAUSED – drift detected!\n"
                   f"Recent {total} trades, WR={wr:.1f}% (critical < {self.drift_critical_threshold}%)")
            if self.notifier:
                self.notifier.send_message(msg)
            print(msg)
        elif wr < self.drift_winrate_threshold:
            msg = (f"⚠️ {acc.name} warning – win rate dropping\n"
                   f"Recent {total} trades, WR={wr:.1f}% (threshold {self.drift_winrate_threshold}%)")
            if self.notifier:
                self.notifier.send_message(msg)
            print(msg)
            
    def predict_next_regime(self, pair, current_regime):
        if self.regime_predictor is None:
            return None

        # ---- 30‑minute cache for H1 data ----
        now = datetime.now(timezone.utc)
        cache = getattr(self, '_regime_data_cache', {})
        if pair in cache:
            cached_time, cached_df = cache[pair]
            if (now - cached_time).total_seconds() < 1800:   # 30 minutes
                df = cached_df.copy()
            else:
                df = None   # expired, fetch fresh
        else:
            df = None

        # Fetch fresh data if not cached or expired
        if df is None:
           # df = self.accounts[0].ai.fetch_data_mt5(pair, bars=200, timeframe=mt5.TIMEFRAME_H1)
           # if df is None or len(df) < 50:
           #     return None
           # df = self.accounts[0].ai.add_indicators(df)
            if df is None:
                return None
            # Store in cache
            cache[pair] = (now, df.copy())
            self._regime_data_cache = cache

        # Add the same features as training
        df['atr_accel'] = df['atr'].diff()
        df['volume_ratio'] = df['volume_ratio'] if 'volume_ratio' in df.columns else (df['volume'] / df['volume'].rolling(20).mean())
        h4 = df['close'].resample('4h').last()
        h4_ema200 = h4.ewm(span=200).mean()
        df['h4_ema200'] = h4_ema200.reindex(df.index, method='ffill')
        df['dist_h4'] = (df['close'] - df['h4_ema200']) / df['h4_ema200'] * 100
        df['hour'] = df.index.hour

        # Current regime one‑hot
        curr_trending = 1 if current_regime == 'trending' else 0
        curr_ranging = 1 if current_regime == 'ranging' else 0
        curr_volatile = 1 if current_regime == 'volatile' else 0

        latest = df.iloc[-1]
        X = np.array([[
            latest['atr_accel'],
            latest['volume_ratio'],
            latest['dist_h4'],
            latest['hour'],
            curr_trending,
            curr_ranging,
            curr_volatile
        ]])
        X_scaled = self.regime_scaler.transform(X)
        pred = self.regime_predictor.predict(X_scaled)[0]
        return pred        
        
    # ---------- Utility: runtime_config sync ----------
    def get_runtime_config(self):
        try:
            with open('runtime_config.json', 'r') as f:
                return json.load(f)
        except:
            return {'active_accounts': [acc.name for acc in self.accounts]}

    # ---------- Telegram command handling ----------
    def check_telegram_commands(self):
        """Return a list of all pending commands since the last check."""
        if not self.notifier:
            return []
        try:
            url = f"https://api.telegram.org/bot{self.notifier.bot_token}/getUpdates"
            if self._last_update_id:
                url += f"?offset={self._last_update_id + 1}"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return []
            data = resp.json()
            if not data.get('ok') or not data['result']:
                return []
            commands = []
            for update in data['result']:
                self._last_update_id = max(self._last_update_id, update['update_id'])
                text = update.get('message', {}).get('text', '').strip().lower()
                if text in ('/stop', '/pause', '/resume', '/status', '/active', '/rejections') or text.startswith('/trade'):
                    commands.append(text)
            return commands
        except:
            return []
    
        
    def handle_command(self, cmd):
        if cmd == '/stop':
            self.notifier.send_message("🛑 Shutting down all accounts.")
            for acc in self.accounts:
                acc.broker.shutdown()
            sys.exit(0)
        elif cmd == '/pause':
            self._paused = True
            for acc in self.accounts:
                acc._paused = True
            self.notifier.send_message("⏸️ All accounts paused.")
        elif cmd == '/resume':
            self._paused = False
            for acc in self.accounts:
                acc._paused = False
            self.notifier.send_message("▶️ All accounts resumed.")
            self.last_status_time = None
        elif cmd == '/active':
            runtime = self.get_runtime_config()
            active = runtime.get('active_accounts', [acc.name for acc in self.accounts])
            msg = f"🎯 Active: {', '.join(active)}"
            if self.notifier:
                self.notifier.send_message(msg)
            else:
                print(msg)    
        elif cmd == '/rejections':
            r = self.rejection_counts
            msg = "📊 Rejection Analytics (since restart):\n"
            msg += f"Total signals: {r['total_signals']}\n"
            msg += f"Accepted: {r['accepted']}\n"
            msg += f"No signal (ML/ICT fail): {r.get('no_signal', 0)}\n"
            msg += f"Confidence: {r['confidence']}\n"
            msg += f"Session: {r['session']}\n"
            msg += f"News: {r['news']}\n"
            msg += f"Correlation: {r['correlation']}\n"
            msg += f"ATR: {r['atr']}\n"
            msg += f"Duplicate: {r['duplicate']}\n"
            msg += f"Opposite: {r['opposite']}\n"
            msg += f"Trending skip: {r['trending_skip']}\n"
            msg += f"Volatile skip (non‑volatile): {r.get('volatile_skip', 0)}\n"
            msg += f"Ranging skip: {r.get('ranging_skip', 0)}\n"
            msg += f"Max trades: {r['max_trades']}\n"
            msg += f"Spread: {r.get('spread', 0)}\n"
            if self.notifier:
                self.notifier.send_message(msg)        
        elif cmd == '/status':
            now = datetime.now(timezone.utc)
            if self.last_status_time and (now - self.last_status_time).total_seconds() < 10:
                return
            self.last_status_time = now
            status_msg = "📊 Status:\n"
            for acc in self.accounts:
                # Force login to this specific account before querying
                mt5.login(acc.broker.account, password=acc.broker.password, server=acc.broker.server)
                bal = acc.get_balance() or 0.0
                positions = acc.broker.get_positions()
                pnl = bal - acc.starting_balance
                status_msg += f"{acc.name}: ${bal:,.2f} | P&L ${pnl:,.2f} | Open {len(positions)}\n"
            self.notifier.send_message(status_msg)    
        elif cmd.startswith('/trade'):
            parts = cmd.strip().split()
            if len(parts) < 2:
                return

            if parts[1].lower() == 'all':
                active = [acc.name for acc in self.accounts]
            elif parts[1].lower() == 'only':
                # /trade only <account name with possible spaces>
                target = ' '.join(parts[2:]).strip().lower()
                # Normalize target to match config names (remove spaces)
                target_clean = target.replace(' ', '')
                active = [acc.name for acc in self.accounts if acc.name.lower() == target_clean]
                if not active:
                    self.notifier.send_message(f"❌ Account '{target}' not found.")
                    return
            else:
                # /trade <account> on/off
                target = parts[1].lower()
                if len(parts) >= 3:
                    action = parts[2].lower()
                else:
                    action = 'on'
                if action == 'only':
                    active = [acc.name for acc in self.accounts if acc.name.lower() == target]
                elif action == 'off':
                    active = [acc.name for acc in self.accounts if acc.name.lower() != target]
                else:  # 'on'
                    active = [acc.name for acc in self.accounts if acc.name.lower() == target]
            with open('runtime_config.json', 'w') as f:
                json.dump({'active_accounts': active}, f)
            self.notifier.send_message(f"🎯 Active accounts: {', '.join(active)}")
            
    # ---------- Filters ----------
    def is_in_session(self, pair):
        if pair not in self.session_hours:
            return True
        hour = datetime.now(timezone.utc).hour
        for start, end in self.session_hours[pair]:
            if start <= end:
                if start <= hour < end:
                    return True
            else:
                if hour >= start or hour < end:
                    return True
        return False

    def is_forex_market_open(self):
        """Return True if a major forex symbol has a fresh tick (< 5 min old)."""
        # Use the same function already defined in real_ai_service
        from real_ai_service import market_is_open
        return market_is_open('EURUSDm') or market_is_open('EURUSD')

    def session_confidence_adjustment(self, pair):
        """
        Return a value to add to the minimum confidence threshold.
        Negative => easier entry (lower threshold)
        Positive => harder entry (raise threshold)
        """
        now = datetime.now(timezone.utc)
        hour = now.hour

        # London / NY overlap (13-16 UTC) -> best quality, lower threshold
        if 13 <= hour < 16:
            return -0.04
        # London session (7-12 UTC) -> good quality, slightly lower
        elif 7 <= hour < 13:
            return -0.02
        # NY session (16-20 UTC) -> decent quality
        elif 16 <= hour < 20:
            return -0.02
        # Asian session (0-7 UTC) -> lower quality, raise threshold
        elif 0 <= hour < 7:
            return 0.05
        # Otherwise (20-24 UTC) -> neutral
        return 0.0
    
    def is_correlated_safe(self, pair, signal, positions):
        USD_CORRELATED = {'EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD'}
        if pair not in USD_CORRELATED:
            return True
        count = 0
        for pos in positions:
            if pos['symbol'] in USD_CORRELATED:
                pos_dir = 'BUY' if pos['type'] == 0 else 'SELL'
                if pos_dir == signal:
                    count += 1
        return count < 3   # block if 3 or more already in the same direction

    # ---------- Duplicate / Opposite checks ----------
    def position_exists(self, symbol, direction, positions):
        for pos in positions:
            # Strip 'm' suffix for comparison
            pos_symbol = pos['symbol'].replace('m', '')
            if pos_symbol == symbol:
                pos_dir = 'BUY' if pos['type'] == 0 else 'SELL'
                if pos_dir == direction:
                    return True
        return False

    def has_opposite(self, symbol, direction, positions):
        for pos in positions:
            if pos['symbol'] == symbol:
                pos_dir = 'BUY' if pos['type'] == 0 else 'SELL'
                if pos_dir != direction:
                    return True
        return False
    
    def apply_atr_trailing_stop(self, acc, pair, atr_val, direction, entry_price, position):
        """
        Modify the SL of an open position based on ATR trailing rules.
        - If trade has moved > 1*ATR in profit, move SL to breakeven.
        - After breakeven, trail the SL 2*ATR behind the current price.
        """
        if not acc.broker.connected:
            return

        symbol_info = mt5.symbol_info_tick(pair)
        if symbol_info is None:
            return

        current_price = symbol_info.bid if direction == 'BUY' else symbol_info.ask
        if current_price is None:
            return

        current_sl = position['sl']
        current_tp = position['tp']
        ticket = position['ticket']

        if direction == 'BUY':
            profit_move = current_price - entry_price
            breakeven_sl = entry_price
            trail_sl = current_price - atr_val * 2.0
            # Ensure the new SL is above the entry (for a buy)
            new_sl = breakeven_sl if current_sl < breakeven_sl else max(current_sl, trail_sl)
        else:  # SELL
            profit_move = entry_price - current_price
            breakeven_sl = entry_price
            trail_sl = current_price + atr_val * 2.0
            new_sl = breakeven_sl if current_sl > breakeven_sl else min(current_sl, trail_sl)

        # Only modify if profit exceeds 1*ATR and the new SL is better than the current one
        if profit_move > atr_val:
            if direction == 'BUY' and new_sl > current_sl:
                # Move stop up
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "sl": new_sl,
                    "tp": current_tp
                }
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   🎯 Trailing stop updated for {pair} – new SL: {new_sl:.5f}")
            elif direction == 'SELL' and new_sl < current_sl:
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "sl": new_sl,
                    "tp": current_tp
                }
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   🎯 Trailing stop updated for {pair} – new SL: {new_sl:.5f}")
    
    def apply_time_exit(self, acc, pair, position, max_hours=24):
        """
        Close trades that have been open for > `max_hours` hours and are losing money.
        Winning trades are left alone to let runners run.
        """
        if not acc.broker.connected:
            return

        # Get the age of the position
        pos_time = datetime.fromtimestamp(position.get('time', 0), tz=timezone.utc)
        now = datetime.now(timezone.utc)
        age_hours = (now - pos_time).total_seconds() / 3600

        if age_hours < max_hours:
            return

        ticket = position['ticket']
        symbol = position['symbol']
        direction = 'BUY' if position['type'] == 0 else 'SELL'
        volume = position['volume']
        current_profit = position.get('profit', 0)

        # Only close if the trade is unprofitable (or flat)
        if current_profit > 0:
            return

        # Get current price to close at market
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return
        close_price = tick.bid if direction == 'BUY' else tick.ask

        # Close the position
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_SELL if direction == 'BUY' else mt5.ORDER_TYPE_BUY,
            "price": close_price,
            "deviation": 10,
            "comment": "time_exit_loss"
        }
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"   ⏰ Time exit – closed losing {symbol} (held {age_hours:.1f}h)")
        else:
            print(f"   ⚠️ Time exit failed for {symbol}")
    
    def is_recent_trade(self, acc, symbol, minutes=30):
        now = datetime.now(timezone.utc)
        last = acc.last_trade_time.get(symbol)
        if last and (now - last).total_seconds() < minutes * 60:
            return True
        return False

    # ---------- Position sizing ----------
    def calc_position_size(self, acc, pair, entry, stop_loss, risk_pct):
        balance = acc.broker.get_balance()
        risk_amount = balance * risk_pct
        # MT5‑correct tick‑value method (preferred)
        try:
            symbol_info = mt5.symbol_info(pair)
            if symbol_info is not None and symbol_info.trade_tick_value > 0 and symbol_info.trade_tick_size > 0:
                risk_per_point = symbol_info.trade_tick_value / symbol_info.trade_tick_size
                sl_dist = abs(entry - stop_loss)
                if sl_dist == 0:
                    return 0.01
                lot = risk_amount / (sl_dist * risk_per_point)
                lot = min(lot, 5.0)          # cap AFTER calculation
                return max(0.01, min(round(lot, 2), 10.0))
        except:
            pass
        # Fallback pip‑based calculation
        pip_value = 0.01 if 'JPY' in pair else 0.0001
        sl_dist = abs(entry - stop_loss)
        if sl_dist == 0:
            return 0.01
        sl_pips = sl_dist / pip_value
        if sl_pips == 0:
            return 0.01
        lot = risk_amount / (sl_pips * 10)
        # Hard cap: maximum 1.0 lot for demo safety
        lot = min(lot, 1.0)
        return max(0.01, min(round(lot, 2), 1.0))
    
        
    # ---------- Daily reset ----------
    def daily_reset(self, acc):
        acc.today = datetime.now().date()
        acc.daily_trades = 0
        acc.daily_pnl = 0.0
        
        # Store previous day's balance for equity curve
        prev_balance = acc.broker.get_balance() or acc.starting_balance
        acc.equity_history.append(prev_balance)
        if len(acc.equity_history) > 20:
            acc.equity_history.pop(0)   # keep only last 20
        
        acc.starting_balance = acc.broker.get_balance()
        acc.daily_peak_balance = acc.starting_balance
        acc.loss_streak = 0
        acc.risk_percent = acc._original_risk
        acc.hedge.reset()
        acc.last_trade_time.clear()
        acc.consecutive_losses = 0
        acc.loss_pause_until = None

    def _fetch_signal_from_daemon(self, pair):
        """Get signal from AI daemon cache instead of computing"""
        try:
            import requests
            resp = requests.get(f'http://localhost:8001/signals/{pair}', timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('signal')
        except Exception as e:
            logger.warning(f"Failed to fetch {pair} from daemon: {e}")
        return None

    # ---------- Manage single account ----------
    def manage_account(self, acc):
        if not acc.enabled or acc._paused or self._paused:
            return
        # Consecutive loss circuit breaker — TEMP disabled
        # if acc.loss_pause_until and datetime.now(timezone.utc) < acc.loss_pause_until:
        #     return

        acc.reconnect()
        # MT5 health check — restart terminal if frozen
        if mt5.terminal_info() is None:
            print("⚠️ MT5 terminal lost — attempting reconnect…")
            mt5.shutdown()
            time.sleep(5)
            if not mt5.initialize():
                print("❌ MT5 reconnect failed — skipping cycle")
                return
            # Re‑login after reconnect
            if not mt5.login(acc.broker.account, password=acc.broker.password, server=acc.broker.server):
                return
            time.sleep(2)
            
        # Force MT5 to switch to THIS account before any queries
        if not mt5.login(acc.broker.account, password=acc.broker.password, server=acc.broker.server):
            print(f"❌ Failed to login to {acc.name}")
            return
        import time
        time.sleep(2)
        for pair in acc.pairs:
            actual_pair = pair + 'm'
            if not mt5.symbol_select(actual_pair, True):
                print(f"⚠️ Could not select {actual_pair}")

        info = mt5.account_info()
        actual_login = info.login if info else 0
        print(f"[MANAGE DEBUG] {acc.name} (login={acc.broker.account}) actual_mt5_login={actual_login} balance={acc.broker.get_balance():.2f}")
        if not acc.broker.connected:
            return
        print(f"[GUARD DEBUG] {acc.name} – market open check: {self.is_forex_market_open()}")

        # Skip signal generation when market is closed
        if not self.is_forex_market_open():
            return

        now = datetime.now(timezone.utc)

        # ---- 0. Daily reset ----
        if now.date() != acc.today:
            if not self.daily_summary_sent_today:
                self.send_daily_summary(acc)
                self.daily_summary_sent_today = True
            self.daily_reset(acc)
            self.check_drift(acc)

        if now.date() != getattr(self, '_last_reset_day', None):
            self.daily_summary_sent_today = False
            self._last_reset_day = now.date()
            self.update_risk_allocation(acc)
            self.update_pair_allocation(acc)

        # ---- 1. Equity and drawdown safety ----
        equity = acc.broker.get_equity()
        if not equity or equity <= 0:
            return

        if acc.starting_balance <= 0:
            acc.starting_balance = equity

        if acc.starting_balance > 0:
            loss = acc.starting_balance - equity
            if loss / acc.starting_balance >= acc.max_daily_loss_percent:
                return

        if equity > acc.daily_peak_balance:
            acc.daily_peak_balance = equity
        if acc.daily_peak_balance > 0:
            trail_dd = (acc.daily_peak_balance - equity) / acc.daily_peak_balance
            if trail_dd >= acc.trail_drawdown_percent:
                return

        # Equity curve filter – only trade when balance is above its 20‑day SMA
        if len(acc.equity_history) >= 20:
            sma20 = sum(acc.equity_history) / 20
            if acc.broker.get_balance() < sma20:
                return   # equity trending down, skip all trading

        if acc.daily_trades >= acc.max_daily_trades:
            #print(f"[DEBUG EXIT] {acc.name} – max trades reached ({acc.daily_trades})")
            return

        positions = acc.broker.get_positions()

        # ---- 2b. ATR trailing stops (with ATR cache) ----
        atr_cache = {}
        for pos in positions:
            # print(f"[TRAIL DEBUG] Checking {pos['symbol']} – profit move vs ATR")
            try:
                pair = pos['symbol']
                if pair not in atr_cache:
                    rates = mt5.copy_rates_from_pos(pair, mt5.TIMEFRAME_H1, 0, 20)
                    if rates is None or len(rates) < 14:
                        continue
                    df = pd.DataFrame(rates)
                    df['high_low'] = df['high'] - df['low']
                    df['high_close'] = abs(df['high'] - df['close'].shift())
                    df['low_close'] = abs(df['low'] - df['close'].shift())
                    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
                    atr_cache[pair] = df['tr'].rolling(14).mean().iloc[-1]
                atr_val = atr_cache[pair]
                direction = 'BUY' if pos['type'] == 0 else 'SELL'
                entry_price = pos['open_price']
                self.apply_atr_trailing_stop(acc, pair, atr_val, direction, entry_price, pos)
            except Exception as e:
                print(f"   ⚠️ Trailing stop error {pair}: {e}")

        # ---- 2c. Time‑based exit (>24h) ----
        for pos in positions:
            try:
                pair = pos['symbol']
                max_h = 6 if acc.name == 'Demo2' else 24
                self.apply_time_exit(acc, pair, pos, max_hours=max_h)
            except Exception as e:
                print(f"   ⚠️ Time exit error {pair}: {e}")

        # ----- Detect and log closed trades (reliable batch method) -----
        current_tickets = set()
        for pos in positions:
            if 'ticket' in pos:
                current_tickets.add(pos['ticket'])
        prev_tickets = getattr(acc, 'previous_tickets', set())
        print(f"[DEBUG] current_tickets: {current_tickets}, prev_tickets: {prev_tickets}")

        newly_closed = prev_tickets - current_tickets
        if newly_closed:
            history = mt5.history_deals_get(now - timedelta(days=1), now)
            if history:
                for deal in history:
                    if deal.entry == 1 and deal.position_id in newly_closed:   # DEAL_ENTRY_OUT
                        ticket = deal.position_id
                        pnl = deal.profit
                        # ---- Update consecutive loss streak ----
                        if pnl < 0:
                            acc.consecutive_losses += 1
                            if acc.consecutive_losses >= acc.consecutive_loss_limit:
                                acc.loss_pause_until = datetime.now(timezone.utc) + timedelta(hours=24)
                                msg = (f"🚨 {acc.name} PAUSED for 24h after "
                                       f"{acc.consecutive_losses} consecutive losses")
                                print(msg)
                                if self.notifier:
                                    self.notifier.send_message(msg)
                        else:
                            acc.consecutive_losses = 0
                        # ---- End streak update ----
                        exit_time = datetime.fromtimestamp(deal.time, tz=timezone.utc)
                        exit_price = deal.price
                        try:
                            acc.logger.log_trade_exit(
                                ticket=ticket,
                                exit_price=exit_price,
                                exit_time=exit_time,
                                pnl=pnl,
                                reason="closed"
                            )
                        except Exception as e:
                            print(f"   ⚠️ Failed to log exit for ticket {ticket}: {e}")
        acc.previous_tickets = current_tickets

        # ---- 3. Process each pair ----
        print(f"[DEBUG PAIRS] {acc.name} – pairs to scan: {acc.pairs}")
        print(f"[LOOP START] {acc.name} – scanning {len(acc.pairs)} pairs")
        for pair in acc.pairs:
            actual_pair = pair + 'm'   # Exness suffix
            # TEMP: clear all cooldowns so signals can flow immediately
            if not getattr(acc, '_cooldown_cleared', False):
                acc.failed_pairs.clear()
                acc._cooldown_cleared = True

            print(f"[LOOP ENTRY] Processing {pair}")
            if acc.daily_trades >= acc.max_daily_trades:
                logger.info(f"REJECTED {acc.name}: max daily trades reached ({acc.daily_trades})")
                return

            # --- Cooldown for previously failed pairs (no money) ---
            last_fail = acc.failed_pairs.get(pair)
            if last_fail:
                age = (now - last_fail).total_seconds()
                print(f"[COOLDOWN CHECK] {pair} – last fail {age:.0f}s ago")
                if age < 1800:
                    print(f"[COOLDOWN SKIP] {pair}")
                    continue

            # Session filter
            if not self.is_in_session(pair):
                logger.info(f"REJECTED {pair}: session filter (acc={acc.name})")
                self.rejection_counts['session'] += 1
                continue
            print(f"[AFTER SESSION] {pair}")
            
            # Demo2: Extended hours for data collection (Asian + London + NY)
            if acc.name == 'Demo2':
                hour = datetime.now(timezone.utc).hour
                if hour < 0 or hour >= 24:  # Trade 0-22 UTC, only skip 22-24
                    continue

            # ---- Market‑closed validation (per‑symbol) ----
            actual_pair = pair + 'm'   # Exness uses 'm' suffix
            symbol_info = mt5.symbol_info(actual_pair)
            if symbol_info is None:
                print(f"[SYMBOL REJECT] {pair} – symbol_info returned None for {actual_pair}")
                continue
            if not symbol_info.trade_mode:
                print(f"[TRADEMODE REJECT] {pair} – trade_mode is False")
                continue

            tick = mt5.symbol_info_tick(actual_pair)   # was 'pair'
            if tick is None:
                print(f"[TICK REJECT] {pair} – tick returned None for {actual_pair}")
                continue

            tick_time = datetime.fromtimestamp(tick.time, tz=timezone.utc)
            age_seconds = max(0, (now - tick_time).total_seconds())
            print(f"[TICK DEBUG] {pair} age={age_seconds:.1f}s")
            if age_seconds > 300:
                print(f"[STALE TICK] {pair} – tick is {age_seconds:.0f}s old, skipping")
                continue

            print(f"[AFTER MARKET CHECK] {pair}")

            # News filter with 5‑minute cache
            now_ts = now.timestamp()
            cached = self._news_cache.get(pair)
            if cached and (now_ts - cached[0]) < 300:   # 5 minutes
                nearby = cached[1]
            else:
                nearby = self.news_filter.is_high_impact_nearby(pair)
                self._news_cache[pair] = (now_ts, nearby)
            if nearby:
                logger.info(f"REJECTED {pair}: news filter (acc={acc.name})")
                self.rejection_counts['news'] += 1
                continue

            
            # Fetch signal from AI Service cache instead of recalculating
            print(f"[FETCH DEBUG] Fetching cached signal for {pair} from AI service")
            try:
                import requests
                resp = requests.get(f'http://localhost:8001/signals/{pair}', timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    signal = data.get('signal')
                else:
                    signal = None
            except:
                print(f"[FETCH DEBUG] AI service unavailable for {pair}")
                signal = None
            print(f"[SIGNAL RETURN] {pair}: signal={'Yes' if signal else 'None'}")
            if signal:
                print(f"[SIGNAL DEBUG] {pair}: entering execution pipeline, conf={signal['confidence']:.3f}, strength={signal.get('strength')}, regime={signal.get('regime')}")
                print(f"[PRE EXEC] {pair} - positions count: {len(positions)}")
                for p in positions:
                    print(f"   pos: symbol={p['symbol']} type={'BUY' if p['type']==0 else 'SELL'} ticket={p.get('ticket')}")
                print(f"[PRE EXEC] {pair} - last_trade_time: {acc.last_trade_time.get(pair)}")
            if signal is None:
                self.rejection_counts['no_signal'] = self.rejection_counts.get('no_signal', 0) + 1
                continue
            self.rejection_counts['total_signals'] += 1

            # Fixed params (simplified - no regime switching)
            params = {
                'min_confidence': acc.min_confidence,
                'risk_percent': acc.risk_percent,
                'sl_atr_mult': 1.5,
                'tp_atr_mult': 2.5
            }

            min_conf = params.get('min_confidence', acc.min_confidence)

            if acc.name == 'Demo2':
                effective_min_conf = 0.47  # Research mode
            else:
                session_adj = self.session_confidence_adjustment(pair)
                effective_min_conf = min_conf + session_adj
                effective_min_conf = max(0.50, min(0.85, effective_min_conf))

            if signal['confidence'] < effective_min_conf:
                print(f"[CONFIDENCE REJECT] {pair} conf={signal['confidence']:.3f} < {effective_min_conf:.3f}")
                logger.info(f"REJECTED {pair}: confidence {signal['confidence']:.3f} < {effective_min_conf:.3f} (acc={acc.name})")
                self.rejection_counts['confidence'] += 1
                continue

            direction = signal['signal']

            if acc.hedge.active and not acc.hedge.allow_signal(direction):
                continue

            if self.position_exists(pair, direction, positions):
                print(f"[DUPLICATE REJECT] {pair} — already have {direction}")
                self.rejection_counts['duplicate'] += 1
                continue
            
            # Limit USD-correlated exposure to max 2 positions
            USD_LONG_PAIRS = {'USDJPY', 'USDCAD', 'USDCHF'}
            USD_SHORT_PAIRS = {'EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD'}
            
            usd_long_count = 0
            usd_short_count = 0
            for pos in positions:
                pos_symbol = pos['symbol'].replace('m', '')
                pos_dir = 'BUY' if pos['type'] == 0 else 'SELL'
                if pos_symbol in USD_LONG_PAIRS and pos_dir == 'BUY':
                    usd_long_count += 1
                if pos_symbol in USD_SHORT_PAIRS and pos_dir == 'SELL':
                    usd_short_count += 1
            
            if pair in USD_LONG_PAIRS and direction == 'BUY' and usd_long_count >= 2:
                print(f"[EXPOSURE REJECT] {pair} - max {usd_long_count} USD long positions")
                continue
            if pair in USD_SHORT_PAIRS and direction == 'SELL' and usd_short_count >= 2:
                print(f"[EXPOSURE REJECT] {pair} - max {usd_short_count} USD short positions")
                continue


            if not acc.hedge.enabled and self.has_opposite(pair, direction, positions):
                self.rejection_counts['opposite'] += 1
                continue

            if self.is_recent_trade(acc, pair, 30):
                print(f"[RECENT TRADE REJECT] {pair} - trade within 30 min")
                continue

            # Base risk
            risk_pct = params.get('risk_percent', acc.risk_percent)

            # Demo2: reduce risk for ranging regimes
            if acc.name == 'Demo2' and regime == 'ranging':
                risk_pct *= 0.5
                print(f"[RANGING ADJUST] {pair} - regime is ranging, risk halved")

            # Correlation filter
            POS_CORRELATED = {
                'EURUSD': ['GBPUSD', 'AUDUSD', 'NZDUSD'],
                'GBPUSD': ['EURUSD', 'AUDUSD', 'NZDUSD'],
                'AUDUSD': ['EURUSD', 'GBPUSD', 'NZDUSD'],
                'NZDUSD': ['EURUSD', 'GBPUSD', 'AUDUSD'],
                'XAUUSD': ['XAGUSD'],
                'XAGUSD': ['XAUUSD'],
            }
            INV_CORRELATED = {
                'EURUSD': ['USDCHF', 'USDCAD'],
                'GBPUSD': ['USDCHF'],
                'AUDUSD': ['USDCAD'],
                'USDCHF': ['EURUSD', 'GBPUSD'],
                'USDCAD': ['EURUSD', 'AUDUSD'],
            }
            USD_PAIRS = {'EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD', 'USDCHF', 'USDCAD', 'XAUUSD', 'XAGUSD'}

            if pair in USD_PAIRS:
                same_count = 0
                inv_count  = 0
                for pos in positions:
                    pos_symbol = pos['symbol']
                    pos_dir    = 'BUY' if pos['type'] == 0 else 'SELL'
                    if pos_symbol in POS_CORRELATED.get(pair, []) and pos_dir == direction:
                        same_count += 1
                    if pos_symbol in INV_CORRELATED.get(pair, []) and pos_dir != direction:
                        inv_count += 1
                    if pos_symbol in INV_CORRELATED and pair in INV_CORRELATED[pos_symbol] and pos_dir != direction:
                        inv_count += 1
                total_exposure = same_count + inv_count
                if total_exposure >= 3:
                    print(f"[CORRELATION REJECT] {pair} total_exposure={total_exposure}")
                    logger.info(f"REJECTED {pair}: correlation limit reached (acc={acc.name})")
                    self.rejection_counts['correlation'] += 1
                    continue
                elif total_exposure == 2:
                    risk_pct *= 0.5
                elif total_exposure == 1:
                    risk_pct *= 0.75

            # ATR filter
            entry_price = signal['entry']
            atr_val = signal.get('atr', entry_price * 0.0015)
            if 'JPY' in pair:
                atr_min = params.get('atr_min_jpy', self.atr_min_jpy)
                atr_max = params.get('atr_max_jpy', self.atr_max_jpy)
            else:
                atr_min = params.get('atr_min_non_jpy', self.atr_min_non_jpy)
                atr_max = params.get('atr_max_non_jpy', self.atr_max_non_jpy)
            if atr_val < atr_min or atr_val > atr_max:
                print(f"[ATR REJECT] {pair} ATR={atr_val:.6f} range=[{atr_min:.6f}, {atr_max:.6f}]")
                logger.info(f"REJECTED {pair}: ATR {atr_val:.6f} out of range [{atr_min:.6f}–{atr_max:.6f}] (acc={acc.name})")
                self.rejection_counts['atr'] += 1
                continue

            sl_mult = params.get('sl_atr_mult', 1.5)
            tp_mult = params.get('tp_atr_mult', 2.5)
            
            # ---- Dynamic TP: scale by confidence ----
            conf = signal['confidence']
            if conf >= 0.70:
                tp_mult *= 1.4   # 40% larger TP for high‑conviction signals
            elif conf >= 0.60:
                tp_mult *= 1.2
            elif conf >= 0.55:
                tp_mult *= 1.0
            else:
                tp_mult *= 0.8   # lower TP for weaker signals
            
            if direction == 'BUY':
                sl = entry_price - atr_val * sl_mult
                tp = entry_price + atr_val * tp_mult
            else:
                sl = entry_price + atr_val * sl_mult
                tp = entry_price - atr_val * tp_mult
                
            # Ensure minimum stop distance for USDSGD (broker requirement)
            if pair == 'USDSGD':
                min_sl_distance = 0.0010  # 10 pips minimum
                if direction == 'BUY' and (entry_price - sl) < min_sl_distance:
                    sl = entry_price - min_sl_distance
                elif direction == 'SELL' and (sl - entry_price) < min_sl_distance:
                    sl = entry_price + min_sl_distance    

            # Phase 2: regime prediction risk adjustment
            if hasattr(self, 'regime_predictor') and self.regime_predictor is not None:
                next_regime = self.predict_next_regime(pair, regime)
                if next_regime == 'volatile':
                    risk_pct *= 0.7
                    if self.notifier and random.random() < 0.05:
                        self.notifier.send_message(f"⚠️ Volatility spike predicted for {pair} – risk reduced")

            if acc.streak_enabled and acc.loss_streak >= acc.streak_threshold:
                risk_pct *= acc.streak_risk_mult

            regime_mult = acc.regime_risk_multipliers.get(regime, 1.0) if hasattr(acc, 'regime_risk_multipliers') else 1.0
            risk_pct *= regime_mult

            pair_weight = acc.pair_risk_weights.get(pair, 1.0) if hasattr(acc, 'pair_risk_weights') else 1.0
            risk_pct *= pair_weight
            
            # ---- Portfolio total risk cap (max 3% of balance) ----
            balance = acc.broker.get_balance()
            open_risk = 0.0
            for pos in positions:
                sl_dist = abs(pos['open_price'] - pos['sl']) if pos['sl'] else 0
                if sl_dist > 0:
                    open_risk += (pos['volume'] * sl_dist * 100000) / balance   # simplified
            if open_risk + risk_pct > 0.03:
                logger.info(f"REJECTED {pair}: total portfolio risk {open_risk*100:.1f}% would exceed 3% cap")
                continue
            
            # Confidence‑based sizing: stronger conviction → larger position
            conf = signal['confidence']
            if conf >= 0.70:
                risk_pct *= 1.2   # 20% larger
            elif conf >= 0.60:
                risk_pct *= 1.0   # normal
            else:
                risk_pct *= 0.8   # 20% smaller for weak signals
  
            lot_size = self.calc_position_size(acc, pair, entry_price, sl, risk_pct)

            # Cap lot sizes for metals
            if pair in ('XAUUSD', 'XAUUSDm', 'GOLD'):
                lot_size = min(lot_size, 0.1)
            elif pair in ('XAGUSD', 'XAGUSDm', 'SILVER'):
                lot_size = min(lot_size, 0.5)

            # ---- Spread filter ----
            tick = mt5.symbol_info_tick(actual_pair)
            if tick is None:
                print(f"[SPREAD REJECT] {pair} tick=None for {actual_pair}")
                continue
            spread = (tick.ask - tick.bid)
            max_spread = atr_val * 0.15
            # Relaxed spread caps for Demo2 data collection
            if acc.name == 'Demo2':
                if 'JPY' in pair:
                    hard_cap = 0.020   # 2 pips for JPY pairs
                else:
                    hard_cap = 0.0015   # 15 pips for other pairs on demo
            else:
                hard_cap = 0.0003 if pair in ('EURUSD','GBPUSD','AUDUSD','NZDUSD') else 0.0004
            if spread > hard_cap:
                print(f"[SPREAD REJECT] {pair} spread={spread:.6f} max_spread={max_spread:.6f} hard_cap={hard_cap:.6f}")
                logger.info(f"REJECTED {pair}: spread too high ({spread:.6f}) (acc={acc.name})")
                self.rejection_counts['spread'] = self.rejection_counts.get('spread', 0) + 1
                continue
            
            # ---- Trade Quality Score ----
            quality = 0
            # ICT + ML agreement (strong signal)
            if signal.get('strength') in ('STRONG', 'MEDIUM'):
                quality += 2
            # Trend alignment (already checked in get_real_signal, passed here)
            quality += 2   # if we reached here, trend filter didn't reject
            # Confidence contribution
            conf = signal['confidence']
            if conf >= 0.65:
                quality += 2
            elif conf >= 0.55:
                quality += 1
            # Spread is reasonable (we just passed spread filter)
            quality += 1
            # Regime is favourable (volatile/ranging, already filtered)
            quality += 1

            quality_threshold = 4 if acc.name == 'Demo2' else 5
            if quality < quality_threshold:
                logger.info(f"REJECTED {pair}: trade quality score {quality}/8 below {quality_threshold}")
                continue

            # ---- EXECUTION DEBUG ----
            print(f"[EXECUTION DEBUG] {pair} signal={direction} conf={signal['confidence']:.3f} account={acc.name}", flush=True)

            order_result = acc.broker.place_market_order(
                actual_pair, direction, entry_price, sl, tp,
                signal['confidence'], volume=lot_size
            )

            ticket = None
            if isinstance(order_result, dict) and 'ticket' in order_result:
                ticket = order_result['ticket']
            elif isinstance(order_result, int):
                ticket = order_result
            result = order_result is not None and order_result != 0

            if result:
                # ---- Verify the trade was placed on the correct account ----
                actual_login = mt5.account_info().login if mt5.account_info() else 0
                if actual_login != acc.broker.account:
                    msg = (f"🚨 CRITICAL: Order placed on wrong account! "
                           f"Expected {acc.broker.account}, got {actual_login}")
                    print(msg)
                    if self.notifier:
                        self.notifier.send_message(msg)
                    continue

                self.rejection_counts['accepted'] += 1
                acc.daily_trades += 1
                acc.last_trade_time[pair] = now
                acc.logger.log_trade_entry(signal, volume=lot_size, ticket=ticket, regime=regime)
                if self.notifier:
                    try:
                        bal = acc.broker.get_balance() or 0.0
                        msg = self.notifier.format_trade_entry(signal, lot_size, bal)
                        self.notifier.send_message(msg)
                    except Exception as e:
                        print(f"Notification error: {e}")
                if self.slack_notifier:
                    try:
                        bal = acc.broker.get_balance() or 0.0
                        msg = self.slack_notifier.format_trade_entry(signal, lot_size, bal)
                        self.slack_notifier.send_message(msg)
                    except Exception as e:
                        print(f"Slack error: {e}")
            else:
                err = str(order_result) if order_result else ""
                if 'No money' in err or '10019' in err:
                    acc.failed_pairs[pair] = now
                    print(f"   ⚠️ {pair} – insufficient margin, will skip for 30 min")
                    
    # ---------- Daily summary ----------
    def send_daily_summary(self, acc):
        if not self.notifier and not self.slack_notifier:
            return
        stats = acc.logger.get_daily_stats()
        msg = f"📅 {acc.name} Daily Summary\n"
        if stats:
            msg += f"Trades: {stats['total_trades']} | P&L: ${(stats['total_pnl'] or 0.0):,.2f} | WR: {stats['win_rate']:.1f}%"
        else:
            msg += "No trades today."
        if self.notifier:
            self.notifier.send_message(msg)
        if self.slack_notifier:
            self.slack_notifier.send_message(msg)
        try:
            report_path = acc.report_gen.generate_report(days=30)
            if report_path and self.notifier:
                self.notifier.send_photo(report_path, caption=f"{acc.name} Daily Report")
        except Exception as e:
            print(f"⚠️ Report failed for {acc.name}: {e}")

    # ---------- Main loop ----------
    def run(self):
        print("\n🤖 Multi‑Account AI Trading Bot RUNNING (Production Safe)...")
        # Initialise attributes used in the loop
        self.last_status_time = None
        self._last_heartbeat = None
        self.daily_summary_sent_today = False
        self._last_reset_day = None

        while True:
            try:
                now = datetime.now(timezone.utc)

                # ----- 0. Daily summary flag reset at midnight -----
                if now.date() != self._last_reset_day:
                    self.daily_summary_sent_today = False
                    self._last_reset_day = now.date()
                
                # Phase 4: Daily Monte Carlo robustness check
                self.daily_monte_carlo_check()
                
                # ----- 1. Heartbeat every 30 minutes -----
                if (self._last_heartbeat is None or
                        (now - self._last_heartbeat).total_seconds() >= 1800):
                    print("💓 Heartbeat – bot alive")
                    self._last_heartbeat = now

                # ----- 2. Process Telegram commands -----
                commands = self.check_telegram_commands()
                if commands:
                    for cmd in commands:
                        self.handle_command(cmd)
                    time.sleep(1)
                    continue                     # skip trading this cycle

                # ----- 2.5. Reload config -----
                try:
                    with open(CONFIG_PATH, 'r') as f:
                        fresh_config = json.load(f)
                    self.session_hours = fresh_config.get('session_hours', {})
                except: pass

                # ----- 3. Reload active account list -----
                runtime = self.get_runtime_config()
                allowed = runtime.get('active_accounts', [acc.name for acc in self.accounts])

                # ----- 4. Manage each account -----
                for acc in self.accounts:
                    if acc.name not in allowed:
                        continue
                    self.manage_account(acc)

                # ----- 5. Sleep until next cycle -----
                time.sleep(self.loop_sleep)

            except KeyboardInterrupt:
                print("\n🛑 Shutting down...")
                for acc in self.accounts:
                    acc.broker.shutdown()
                break
            except Exception as e:
                print(f"❌ AutoTrader crashed: {e}")
                if self.notifier:
                    self.notifier.send_message(f"❌ Error: {e}")
                time.sleep(60)
                 

if __name__ == "__main__":
    trader = AutoTrader()
    trader.run()