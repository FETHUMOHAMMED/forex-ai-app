"""
Volume 9.5: Institutional Trade Filtering & Data Expansion
Enforces evidence-based pair/session/regime filters.
Blocks proven losers, allows proven winners.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import Tuple, Dict


class InstitutionalFilter:
    """
    Hard filters based on 157 data points of evidence.
    These are NON-NEGOTIABLE gates - proven losers get blocked.
    """

    # Evidence-based pair classification
    PAIR_RULES = {
        'USDJPY':  {'status': 'ALLOW',   'wr': 64.3, 'trades': 14, 'reason': 'Best performer'},
        'NZDUSD':  {'status': 'ALLOW',   'wr': 51.7, 'trades': 29, 'reason': 'Strong in RANGING'},
        'EURUSD':  {'status': 'ALLOW',   'wr': 45.0, 'trades': 20, 'reason': 'Consistent performer'},
        'GBPUSD':  {'status': 'ALLOW',   'wr': 40.9, 'trades': 22, 'reason': 'Acceptable'},
        'USDCAD':  {'status': 'CAUTION', 'wr': 45.5, 'trades': 22, 'reason': 'Only SWEEP_SELL regime'},
        'AUDUSD':  {'status': 'BLOCK',   'wr': 30.0, 'trades': 20, 'reason': 'Below 35% WR threshold'},
        'USDCHF':  {'status': 'BLOCK',   'wr': 0.0,  'trades': 4,  'reason': 'Proven loser'},
        'USDSGD':  {'status': 'BLOCK',   'wr': 0.0,  'trades': 4,  'reason': 'Proven loser'},
    }

    # Session rules
    SESSION_RULES = {
        'LONDON':  {'status': 'ALLOW', 'wr': 47, 'reason': 'Best session'},
        'ASIAN':   {'status': 'ALLOW', 'wr': 40, 'reason': 'Acceptable, near breakeven'},
        'OVERLAP': {'status': 'BLOCK', 'wr': 21, 'reason': 'Heavy losses'},
        'NY':      {'status': 'BLOCK', 'wr': 0,  'reason': 'Zero wins'},
    }

    # Regime rules
    REGIME_RULES = {
        'RANGING':     {'status': 'ALLOW',   'wr': 54.4, 'reason': 'Best regime'},
        'SWEEP_SELL':  {'status': 'ALLOW',   'wr': 53.3, 'reason': 'Liquidity sweep edge'},
        'NEUTRAL':     {'status': 'CAUTION', 'wr': 40.0, 'reason': 'Marginal'},
        'BREAKOUT':    {'status': 'BLOCK',   'wr': 28.9, 'reason': 'Below 30% WR'},
        'SWEEP_BUY':   {'status': 'BLOCK',   'wr': 0.0,  'reason': 'Zero wins'},
    }

    def check_pair(self, pair: str) -> Tuple[bool, str]:
        """Check if pair is allowed to trade"""
        rule = self.PAIR_RULES.get(pair, {'status': 'BLOCK', 'reason': 'Unknown pair'})
        if rule['status'] == 'ALLOW':
            return True, f"ALLOW: {pair} ({rule['wr']}% WR, {rule['trades']} trades)"
        elif rule['status'] == 'CAUTION':
            return True, f"CAUTION: {pair} - {rule['reason']} ({rule['wr']}% WR)"
        else:
            return False, f"BLOCK: {pair} - {rule['reason']}"

    def check_session(self, session: str) -> Tuple[bool, str]:
        """Check if session is allowed"""
        rule = self.SESSION_RULES.get(session, {'status': 'BLOCK', 'reason': 'Unknown session'})
        if rule['status'] == 'ALLOW':
            return True, f"ALLOW: {session} session ({rule['wr']}% WR)"
        else:
            return False, f"BLOCK: {session} session - {rule['reason']}"

    def check_regime(self, regime: str) -> Tuple[bool, str]:
        """Check if regime is allowed"""
        rule = self.REGIME_RULES.get(regime, {'status': 'CAUTION', 'reason': 'Unknown regime'})
        if rule['status'] == 'ALLOW':
            return True, f"ALLOW: {regime} regime ({rule['wr']}% WR)"
        elif rule['status'] == 'CAUTION':
            return True, f"CAUTION: {regime} regime - {rule['reason']}"
        else:
            return False, f"BLOCK: {regime} regime - {rule['reason']}"

    def full_check(self, pair: str, session: str, regime: str) -> Tuple[bool, str, Dict]:
        """
        Complete filter check.
        Returns: (passed, reason, details)
        """
        details = {}
        
        # Pair check
        pair_ok, pair_reason = self.check_pair(pair)
        details['pair'] = {'passed': pair_ok, 'reason': pair_reason}
        if not pair_ok:
            return False, pair_reason, details
        
        # Session check
        session_ok, session_reason = self.check_session(session)
        details['session'] = {'passed': session_ok, 'reason': session_reason}
        if not session_ok:
            return False, session_reason, details
        
        # Regime check
        regime_ok, regime_reason = self.check_regime(regime)
        details['regime'] = {'passed': regime_ok, 'reason': regime_reason}
        if not regime_ok:
            return False, regime_reason, details
        
        return True, "ALL FILTERS PASSED", details

    def get_allowed_pairs(self) -> list:
        """Get list of pairs allowed to trade"""
        return [p for p, r in self.PAIR_RULES.items() if r['status'] in ('ALLOW', 'CAUTION')]

    def summary(self):
        """Print filter summary"""
        print("=" * 55)
        print("  INSTITUTIONAL FILTER v9.5")
        print("=" * 55)
        
        print("\n  PAIR FILTERS:")
        for pair, rule in self.PAIR_RULES.items():
            marker = {'ALLOW': '[+]', 'CAUTION': '[~]', 'BLOCK': '[X]'}
            print(f"    {marker[rule['status']]} {pair:8s} {rule['status']:8s} {rule['wr']}% WR - {rule['reason']}")
        
        print("\n  SESSION FILTERS:")
        for session, rule in self.SESSION_RULES.items():
            marker = {'ALLOW': '[+]', 'BLOCK': '[X]'}
            print(f"    {marker[rule['status']]} {session:8s} {rule['status']:8s} {rule['wr']}% WR - {rule['reason']}")
        
        print("\n  REGIME FILTERS:")
        for regime, rule in self.REGIME_RULES.items():
            marker = {'ALLOW': '[+]', 'CAUTION': '[~]', 'BLOCK': '[X]'}
            print(f"    {marker[rule['status']]} {regime:12s} {rule['status']:8s} {rule['wr']}% WR - {rule['reason']}")
        
        print("=" * 55)


if __name__ == "__main__":
    f = InstitutionalFilter()
    f.summary()
    
    print("\n  Full checks:")
    tests = [
        ("USDJPY", "LONDON", "RANGING"),
        ("AUDUSD", "LONDON", "RANGING"),
        ("NZDUSD", "NY", "RANGING"),
        ("GBPUSD", "ASIAN", "BREAKOUT"),
    ]
    for pair, session, regime in tests:
        ok, reason, details = f.full_check(pair, session, regime)
        print(f"    {'[OK]' if ok else '[XX]'} {pair}+{session}+{regime}: {reason}")
