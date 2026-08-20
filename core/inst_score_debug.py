"""
Institutional Score Breakdown - Shows which components contribute.
"""
import sys, os, MetaTrader5 as mt5, pandas as pd
sys.path.insert(0, '.')

from institutional.market_microstructure import MarketMicrostructure
from institutional.liquidity_intelligence import LiquidityIntelligence
from institutional.institutional_structure import InstitutionalStructure

mm = MarketMicrostructure()
liq = LiquidityIntelligence()
struct = InstitutionalStructure()
mt5.initialize()

for pair in ['EURUSD', 'GBPUSD']:
    symbol = pair + 'm'
    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 200)
    df = pd.DataFrame(rates)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    ms = mm.analyze(pair, df)
    lq_result = liq.analyze(pair, df)
    st_result = struct.analyze(pair, df)
    
    print(f"\n{'='*50}")
    print(f"  {pair} INSTITUTIONAL SCORE BREAKDOWN")
    print(f"{'='*50}")
    print(f"  Microstructure Score: {ms.microstructure_score:.0f}/100")
    print(f"    Bias: {ms.institutional_bias}")
    print(f"    Dealer: {ms.dealer_pressure}")
    print(f"    Volume Delta: {ms.volume_delta:+.3f}")
    print(f"    Continuation Prob: {ms.continuation_probability:.0%}")
    print(f"")
    print(f"  Liquidity Score: {lq_result.liquidity_score:.0f}/100")
    print(f"    State: {lq_result.liquidity_state}")
    print(f"    Sweep: {lq_result.sweep_detected} dir={lq_result.sweep_direction}")
    print(f"    Strength: {lq_result.sweep_strength:.2f}")
    print(f"")
    print(f"  Structure Score: {st_result.structure_score:.0f}/100")
    print(f"    Bias: {st_result.structure_bias}")
    print(f"    Phase: {st_result.market_phase}")
    print(f"    Continuation: {st_result.continuation_prob:.0%}")
    print(f"")
    
    # Combined score (same formula as signal pipeline)
    combined = ms.microstructure_score * 0.4 + lq_result.liquidity_score * 0.35 + st_result.structure_score * 0.25
    print(f"  COMBINED: {combined:.0f}/100 (threshold: 55)")
    print(f"  {'WOULD PASS' if combined >= 55 else 'REJECTED - below 55'}")
    print(f"")
    
    # Why is it low?
    print(f"  WEAK COMPONENTS:")
    if ms.microstructure_score < 55: print(f"    Microstructure: {ms.microstructure_score:.0f} (needs 55)")
    if lq_result.liquidity_score < 55: print(f"    Liquidity: {lq_result.liquidity_score:.0f} (needs 55)")
    if st_result.structure_score < 55: print(f"    Structure: {st_result.structure_score:.0f} (needs 55)")
    if ms.dealer_pressure == 'NEUTRAL': print(f"    Dealer is NEUTRAL - contributes 0")
    if ms.institutional_bias == 'NEUTRAL': print(f"    Bias is NEUTRAL - contributes 0")
    if not lq_result.sweep_detected: print(f"    No sweep detected - low liquidity score")

mt5.shutdown()
