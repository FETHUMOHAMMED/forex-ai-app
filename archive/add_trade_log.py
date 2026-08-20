with open("ai-service/auto_trader_exness.py","r",encoding="utf-8") as f:
    content = f.read()

old = "acc.logger.log_trade_entry(signal, volume=lot_size, ticket=ticket, regime=regime, account=acc.name)"
new = "acc.logger.log_trade_entry(signal, volume=lot_size, ticket=ticket, regime=regime, account=acc.name)\n                logger.info(f'[TRADE LOGGED] account={acc.name} pair={pair} ticket={ticket}')"

if old in content:
    content = content.replace(old, new)
    print("Added trade log line")
else:
    print("Pattern not found - checking...")
    for i, line in enumerate(content.split('\n')):
        if 'log_trade_entry' in line:
            print(f"  Line {i}: {line.strip()}")

with open("ai-service/auto_trader_exness.py","w",encoding="utf-8") as f:
    f.write(content)
