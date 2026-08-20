# Fix: Use regime predictor when signal has UNKNOWN regime
content = open('ai-service/auto_trader_exness.py', encoding='utf-8', errors='replace').read()

old = '''            # P0: Regime validation - UNKNOWN regime = REJECT
            regime = signal.get('regime', 'UNKNOWN')
            if regime == 'UNKNOWN' or regime is None:
                logger.info(f"REJECTED {pair}: UNKNOWN regime (acc={acc.name})")
                self.rejection_counts['regime'] = self.rejection_counts.get('regime', 0) + 1
                continue'''

new = '''            # P0: Regime validation - try predictor, then reject if still UNKNOWN
            regime = signal.get('regime', 'UNKNOWN')
            if regime == 'UNKNOWN' or regime is None:
                # Try using regime predictor
                if self.regime_predictor is not None:
                    try:
                        predicted = self.predict_next_regime(pair, 'volatile')
                        if predicted and predicted != 'UNKNOWN':
                            regime = predicted
                            signal['regime'] = predicted
                            print(f"[REGIME FIX] {pair}: UNKNOWN -> {predicted} (via predictor)")
                        else:
                            logger.info(f"REJECTED {pair}: UNKNOWN regime (acc={acc.name})")
                            self.rejection_counts['regime'] = self.rejection_counts.get('regime', 0) + 1
                            continue
                    except Exception as e:
                        logger.info(f"REJECTED {pair}: UNKNOWN regime, predictor failed: {e} (acc={acc.name})")
                        self.rejection_counts['regime'] = self.rejection_counts.get('regime', 0) + 1
                        continue
                else:
                    logger.info(f"REJECTED {pair}: UNKNOWN regime (acc={acc.name})")
                    self.rejection_counts['regime'] = self.rejection_counts.get('regime', 0) + 1
                    continue'''

if old in content:
    content = content.replace(old, new)
    open('ai-service/auto_trader_exness.py', 'w', encoding='utf-8').write(content)
    print('Fixed: UNKNOWN regime now tries predictor before rejecting')
else:
    print('Pattern not found - checking...')
    import re
    matches = re.findall(r'regime.*UNKNOWN.*REJECT', content)
    for m in matches[:2]:
        print(f'  Found: {m.strip()[:80]}')
