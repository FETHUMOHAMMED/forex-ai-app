import sqlite3
import pandas as pd
from datetime import datetime

conn = sqlite3.connect('trades.db')

df = pd.read_sql_query("SELECT pair, pnl, timestamp, institutional_bias, institutional_score, dealer_pressure, liquidity_state, continuation_prob FROM trades WHERE pnl IS NOT NULL AND institutional_bias IS NOT NULL", conn)

def get_session(ts):
    try:
        dt = datetime.fromisoformat(ts)
        hour = dt.hour
        if 3 <= hour < 12:
            return 'LONDON'
        elif 12 <= hour < 20:
            return 'NY'
        elif 20 <= hour or hour < 3:
            return 'ASIAN'
        else:
            return 'OVERLAP'
    except:
        return 'UNKNOWN'

df['session'] = df['timestamp'].apply(get_session)
df['win'] = df['pnl'] > 0
total = len(df)
wins = df['win'].sum()
net_pnl = df['pnl'].sum()
print(f'Total trades: {total} | Wins: {wins} | WR: {wins/total*100:.1f}%')
print(f'Net PnL: {net_pnl:+.2f}')
print()

print('=' * 60)
print('1. INSTITUTIONAL SCORE vs WIN RATE')
print('=' * 60)
brackets = [(0,20), (20,40), (40,60), (60,80), (80,101)]
for lo, hi in brackets:
    mask = (df['institutional_score'] >= lo) & (df['institutional_score'] < hi)
    subset = df[mask]
    if len(subset) > 0:
        wr = subset['win'].sum()/len(subset)*100
        pnl = subset['pnl'].sum()
        print(f'  Score {lo}-{hi}: {len(subset):2d} trades, {wr:5.1f}% WR, PnL {pnl:+.2f}')
    else:
        print(f'  Score {lo}-{hi}: 0 trades')

print()
print('=' * 60)
print('2. LIQUIDITY STATE vs WIN RATE')
print('=' * 60)
for state in df['liquidity_state'].dropna().unique():
    subset = df[df['liquidity_state'] == state]
    wr = subset['win'].sum()/len(subset)*100
    pnl = subset['pnl'].sum()
    print(f'  {state:25s}: {len(subset):2d} trades, {wr:5.1f}% WR, PnL {pnl:+.2f}')

print()
print('=' * 60)
print('3. INSTITUTIONAL BIAS vs WIN RATE')
print('=' * 60)
for bias in df['institutional_bias'].dropna().unique():
    subset = df[df['institutional_bias'] == bias]
    wr = subset['win'].sum()/len(subset)*100
    pnl = subset['pnl'].sum()
    print(f'  {bias:25s}: {len(subset):2d} trades, {wr:5.1f}% WR, PnL {pnl:+.2f}')

print()
print('=' * 60)
print('4. DEALER PRESSURE vs WIN RATE')
print('=' * 60)
for dp in sorted(df['dealer_pressure'].dropna().unique()):
    subset = df[df['dealer_pressure'] == dp]
    wr = subset['win'].sum()/len(subset)*100
    pnl = subset['pnl'].sum()
    print(f'  {dp:25s}: {len(subset):2d} trades, {wr:5.1f}% WR, PnL {pnl:+.2f}')

print()
print('=' * 60)
print('5. CONTINUATION PROBABILITY vs WIN RATE')
print('=' * 60)
brackets = [(0,0.3), (0.3,0.5), (0.5,0.7), (0.7,1.01)]
for lo, hi in brackets:
    mask = (df['continuation_prob'] >= lo) & (df['continuation_prob'] < hi)
    subset = df[mask]
    if len(subset) > 0:
        wr = subset['win'].sum()/len(subset)*100
        pnl = subset['pnl'].sum()
        print(f'  Prob {lo:.1f}-{hi:.1f}: {len(subset):2d} trades, {wr:5.1f}% WR, PnL {pnl:+.2f}')

print()
print('=' * 60)
print('6. USDJPY + LONDON (Target Config)')
print('=' * 60)
target = df[(df['pair']=='USDJPY') & (df['session']=='LONDON')]
if len(target) > 0:
    wr = target['win'].sum()/len(target)*100
    pnl = target['pnl'].sum()
    print(f'  Trades: {len(target)}, WR: {wr:.1f}%, PnL: {pnl:+.2f}')
    print()
    for lo, hi in [(0,40), (40,70), (70,101)]:
        mask = (target['institutional_score'] >= lo) & (target['institutional_score'] < hi)
        sub = target[mask]
        if len(sub) > 0:
            wr2 = sub['win'].sum()/len(sub)*100
            pnl2 = sub['pnl'].sum()
            print(f'    Score {lo}-{hi}: {len(sub)} trades, {wr2:.0f}% WR, PnL {pnl2:+.2f}')

print()
print('=' * 60)
print('7. USDJPY FEATURE BREAKDOWN')
print('=' * 60)
uj = df[df['pair']=='USDJPY']
if len(uj) > 0:
    uj_wr = uj['win'].sum()/len(uj)*100
    uj_pnl = uj['pnl'].sum()
    print(f'  Total USDJPY: {len(uj)} trades, WR: {uj_wr:.1f}%, PnL: {uj_pnl:+.2f}')
    for state in uj['liquidity_state'].dropna().unique():
        sub = uj[uj['liquidity_state']==state]
        s_wr = sub['win'].sum()/len(sub)*100 if len(sub) > 0 else 0
        print(f'    {state}: {len(sub)} trades, {s_wr:.0f}% WR')

conn.close()
