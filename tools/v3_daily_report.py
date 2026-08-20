"""V3 Daily Report - Separate RAW vs QUALIFIED performance."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.common import get_db
from datetime import datetime

def safe_fmt(value, fmt_str="${:.2f}"):
    if value is None: return "N/A"
    try: return fmt_str.format(value)
    except: return str(value)

def main():
    print("=" * 60)
    print("  V3_REGIME DAILY REPORT (Live_Micro)")
    print("=" * 60)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    conn = get_db()
    cursor = conn.cursor()
    
    FILTER = "strategy_version = 'V3_REGIME' AND account = 'Live_Micro'"
    
    # TODAY
    cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(pnl), 0) FROM trades WHERE {FILTER} AND date(timestamp) = date('now') AND exit_time IS NOT NULL")
    today_closed = cursor.fetchone()
    
    cursor.execute(f"SELECT COUNT(*) FROM trades WHERE {FILTER} AND date(timestamp) = date('now') AND exit_time IS NULL")
    today_open = cursor.fetchone()[0]
    
    print(f"\n  TODAY:")
    print(f"    Opened: {today_closed[0] + today_open}")
    print(f"    Closed: {today_closed[0]} | PnL: {safe_fmt(today_closed[1])}")
    print(f"    Open:   {today_open}")
    
    # OPERATIONAL (RAW)
    cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(pnl), 0), COALESCE(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END), 0) FROM trades WHERE {FILTER} AND exit_time IS NOT NULL")
    raw = cursor.fetchone()
    
    cursor.execute(f"SELECT COUNT(*) FROM trades WHERE {FILTER} AND exit_time IS NULL")
    raw_open = cursor.fetchone()[0]
    
    print(f"\n  OPERATIONAL (Raw V3):")
    print(f"    Total raw:       {raw[0] + raw_open}")
    print(f"    Raw closed:      {raw[0]}")
    print(f"    Raw P&L:         {safe_fmt(raw[1])}")
    if raw[0] > 0:
        print(f"    Raw win rate:    {(raw[2]/raw[0]*100):.0f}%")
    print(f"    Raw open:        {raw_open}")
    
    # VALIDATED (QUALIFIED)
    cursor.execute(f"SELECT COUNT(*) FROM trades WHERE {FILTER} AND execution_contract_valid = 1 AND exit_time IS NOT NULL AND mt5_position_id IS NOT NULL")
    qual_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE {FILTER} AND execution_contract_valid = 1 AND exit_time IS NOT NULL")
    qual_pnl = cursor.fetchone()[0]
    
    print(f"\n  VALIDATED (Qualified V3):")
    print(f"    Qualified closed: {qual_count}")
    print(f"    Qualified P&L:    {safe_fmt(qual_pnl)}")
    if qual_count > 0:
        cursor.execute(f"SELECT COALESCE(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END), 0) FROM trades WHERE {FILTER} AND execution_contract_valid = 1")
        qual_wins = cursor.fetchone()[0]
        print(f"    Qualified WR:     {(qual_wins/qual_count*100):.0f}%")
    else:
        print(f"    Qualified WR:     N/A (0 qualified)")
    print(f"    Profit factor:    N/A")
    print(f"    Expectancy:       N/A")
    
    # MT5 Floating
    from tools.common import check_mt5
    mt5 = check_mt5()
    if mt5['connected'] and raw_open > 0:
        unrealized = mt5['equity'] - mt5['balance']
        print(f"\n  Floating P&L: ${unrealized:,.2f} (from MT5)")
    
    # Excluded
    cursor.execute("SELECT COUNT(*), COALESCE(SUM(pnl), 0) FROM trades WHERE strategy_version = 'V3_REGIME' AND account != 'Live_Micro'")
    demo = cursor.fetchone()
    if demo[0] > 0:
        print(f"\n  Excluded (Demo/Other): {demo[0]} trades | PnL: {safe_fmt(demo[1])}")
    
    conn.close()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
