with open("core/signal_pipeline_v2.py","r",encoding="utf-8") as f:
    content = f.read()

old = "        # Determine direction\n        direction = None\n        if ml_signal and ict_buy and ml_signal == 'BUY':\n            direction = 'BUY'\n        elif ml_signal and ict_sell and ml_signal == 'SELL':\n            direction = 'SELL'"

new = "        # ICT conflict check\n        if ict_buy and ict_sell:\n            sig = TradeSignal(pair=pair, direction='NONE', confidence=ml_confidence,\n                            entry=current_price, stop_loss=0, take_profit=0)\n            sig.reject('ICT conflict: both buy and sell signals')\n            return sig\n        \n        # Determine direction\n        direction = None\n        if ml_signal and ict_buy and ml_signal == 'BUY':\n            direction = 'BUY'\n        elif ml_signal and ict_sell and ml_signal == 'SELL':\n            direction = 'SELL'"

if old in content:
    content = content.replace(old, new)
    print("ICT conflict filter added")
else:
    print("Pattern not found")

with open("core/signal_pipeline_v2.py","w",encoding="utf-8") as f:
    f.write(content)
