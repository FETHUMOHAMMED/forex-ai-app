"""
Phase 6: Validate Institutional Microstructure
Compares institutional analysis against actual trade outcomes.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ai-service'))

import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai-service', 'trades.db')

def validate():
    conn = sqlite3.connect(DB_PATH)
    
    # Check if institutional columns have data
    query = """
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN institutional_bias IS NOT NULL THEN 1 ELSE 0 END) as with_inst,
        SUM(CASE WHEN institutional_bias = 'BULLISH' THEN 1 ELSE 0 END) as bullish,
        SUM(CASE WHEN institutional_bias = 'BEARISH' THEN 1 ELSE 0 END) as bearish,
        SUM(CASE WHEN institutional_bias = 'NEUTRAL' THEN 1 ELSE 0 END) as neutral
    FROM trades 
    WHERE pnl IS NOT NULL
    """
    
    df = pd.read_sql_query(query, conn)
    print("=" * 60)
    print("  INSTITUTIONAL DATA COLLECTION STATUS")
    print("=" * 60)
    print(f"  Total closed trades: {df['total'].iloc[0]}")
    print(f"  With institutional data: {df['with_inst'].iloc[0]}")
    print(f"  Bullish signals: {df['bullish'].iloc[0]}")
    print(f"  Bearish signals: {df['bearish'].iloc[0]}")
    print(f"  Neutral signals: {df['neutral'].iloc[0]}")
    print()
    
    # Compare institutional bias vs trade outcome
    query2 = """
    SELECT 
        institutional_bias,
        COUNT(*) as trades,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(AVG(pnl), 2) as avg_pnl,
        ROUND(SUM(pnl), 2) as total_pnl
    FROM trades 
    WHERE pnl IS NOT NULL 
      AND institutional_bias IS NOT NULL
    GROUP BY institutional_bias
    ORDER BY total_pnl DESC
    """
    
    df2 = pd.read_sql_query(query2, conn)
    if len(df2) > 0:
        print("=" * 60)
        print("  PERFORMANCE BY INSTITUTIONAL BIAS")
        print("=" * 60)
        for _, row in df2.iterrows():
            wr = (row['wins'] / row['trades'] * 100) if row['trades'] > 0 else 0
            print(f"  {row['institutional_bias']:10s}: {row['trades']:3d} trades | WR: {wr:5.1f}% | PnL: ${row['total_pnl']:8.2f}")
        print()
    
    # Compare continuation probability vs outcome
    query3 = """
    SELECT 
        CASE 
            WHEN continuation_prob >= 0.60 THEN 'HIGH (60%+)'
            WHEN continuation_prob >= 0.50 THEN 'MEDIUM (50-60%)'
            WHEN continuation_prob >= 0.40 THEN 'LOW (40-50%)'
            ELSE 'VERY LOW (<40%)'
        END as cont_bucket,
        COUNT(*) as trades,
        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(AVG(pnl), 2) as avg_pnl
    FROM trades 
    WHERE pnl IS NOT NULL 
      AND continuation_prob IS NOT NULL
    GROUP BY cont_bucket
    ORDER BY cont_bucket
    """
    
    df3 = pd.read_sql_query(query3, conn)
    if len(df3) > 0:
        print("=" * 60)
        print("  PERFORMANCE BY CONTINUATION PROBABILITY")
        print("=" * 60)
        for _, row in df3.iterrows():
            wr = (row['wins'] / row['trades'] * 100) if row['trades'] > 0 else 0
            print(f"  {row['cont_bucket']:25s}: {row['trades']:3d} trades | WR: {wr:5.1f}% | Avg PnL: ${row['avg_pnl']:8.2f}")
        print()
    
    # Recommendation
    print("=" * 60)
    print("  RECOMMENDATION")
    print("=" * 60)
    
    total_with_inst = df['with_inst'].iloc[0]
    if total_with_inst < 20:
        print(f"  Need more data. Currently {total_with_inst} trades with institutional data.")
        print(f"  Target: 50+ trades for meaningful analysis.")
    else:
        # Check if bullish trades outperform
        bullish_pnl = df2[df2['institutional_bias'] == 'BULLISH']['total_pnl'].sum() if 'BULLISH' in df2['institutional_bias'].values else 0
        bearish_pnl = df2[df2['institutional_bias'] == 'BEARISH']['total_pnl'].sum() if 'BEARISH' in df2['institutional_bias'].values else 0
        if bullish_pnl > 0 and bearish_pnl < 0:
            print("  Institutional filter is WORKING. Bullish trades profitable, bearish trades losing.")
        else:
            print("  More data needed to validate institutional filter effectiveness.")
    
    conn.close()

if __name__ == '__main__':
    validate()