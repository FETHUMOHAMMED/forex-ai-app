"""Fix daily report to separate Raw vs Qualified performance."""
content = open('tools/v3_daily_report.py').read()

# Add qualified section using the canonical checker
old = '''    # ALL TIME (Live_Micro V3)
    cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(pnl), 0), COALESCE(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END), 0) FROM trades WHERE {FILTER} AND exit_time IS NOT NULL")
    all_closed = cursor.fetchone()

    cursor.execute(f"SELECT COUNT(*) FROM trades WHERE {FILTER} AND exit_time IS NULL")
    all_open = cursor.fetchone()[0]

    print(f"\\n  ALL TIME (Live_Micro V3):")
    print(f"    Total:  {all_closed[0] + all_open}")
    print(f"    Closed: {all_closed[0]} | PnL: {safe_fmt(all_closed[1])}")
    print(f"    Wins: {all_closed[2]} | Win Rate: {(all_closed[2]/all_closed[0]*100):.0f}%" if all_closed[0] > 0 else f"    Win Rate: N/A")
    print(f"    Open:   {all_open}")'''

new = '''    # RAW OPERATIONAL (all trades)
    cursor.execute(f"SELECT COUNT(*), COALESCE(SUM(pnl), 0), COALESCE(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END), 0) FROM trades WHERE {FILTER} AND exit_time IS NOT NULL")
    raw_closed = cursor.fetchone()

    cursor.execute(f"SELECT COUNT(*) FROM trades WHERE {FILTER} AND exit_time IS NULL")
    raw_open = cursor.fetchone()[0]

    print(f"\\n  OPERATIONAL (Raw V3):")
    print(f"    Total raw:      {raw_closed[0] + raw_open}")
    print(f"    Raw closed:     {raw_closed[0]}")
    print(f"    Raw P&L:        {safe_fmt(raw_closed[1])}")
    if raw_closed[0] > 0:
        print(f"    Raw win rate:   {(raw_closed[2]/raw_closed[0]*100):.0f}%")
    print(f"    Raw open:       {raw_open}")

    # VALIDATED (qualified only)
    cursor.execute(f"SELECT COUNT(*) FROM trades WHERE {FILTER} AND execution_contract_valid = 1 AND exit_time IS NOT NULL AND mt5_position_id IS NOT NULL")
    qualified_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE {FILTER} AND execution_contract_valid = 1 AND exit_time IS NOT NULL")
    qualified_pnl = cursor.fetchone()[0]
    
    print(f"\\n  VALIDATED (Qualified V3):")
    print(f"    Qualified closed: {qualified_count}")
    print(f"    Qualified P&L:    {safe_fmt(qualified_pnl)}")
    if qualified_count > 0:
        cursor.execute(f"SELECT COALESCE(SUM(CASE WHEN result='WIN' THEN 1 ELSE 0 END), 0) FROM trades WHERE {FILTER} AND execution_contract_valid = 1")
        qualified_wins = cursor.fetchone()[0]
        print(f"    Qualified WR:     {(qualified_wins/qualified_count*100):.0f}%")
    else:
        print(f"    Qualified WR:     N/A (0 qualified)")
    print(f"    Profit factor:    N/A")
    print(f"    Expectancy:       N/A")'''

content = content.replace(old, new)
open('tools/v3_daily_report.py', 'w').write(content)
print('Fixed daily report: separate RAW vs QUALIFIED')
