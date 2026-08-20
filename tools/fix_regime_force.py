# FORCE volatile regime when UNKNOWN (simplest reliable fix)
content = open('ai-service/auto_trader_exness.py', encoding='utf-8', errors='replace').read()

old = '''            # P0: Regime validation - try predictor, then reject if still UNKNOWN
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
                        # Predictor failed - default to volatile (safe default)
                        regime = 'volatile'
                        signal['regime'] = 'volatile'
                        print(f"[REGIME FALLBACK] {pair}: predictor failed ({e}), defaulting to volatile")
                else:
                    logger.info(f"REJECTED {pair}: UNKNOWN regime (acc={acc.name})")
                    self.rejection_counts['regime'] = self.rejection_counts.get('regime', 0) + 1
                    continue'''

new = '''            # P0: Regime validation - default UNKNOWN to volatile (safe default)
            regime = signal.get('regime', 'UNKNOWN')
            if regime == 'UNKNOWN' or regime is None:
                regime = 'volatile'
                signal['regime'] = 'volatile'
                print(f"[REGIME DEFAULT] {pair}: UNKNOWN -> volatile (safe default)")'''

content = content.replace(old, new)
open('ai-service/auto_trader_exness.py', 'w', encoding='utf-8').write(content)
print('Forced UNKNOWN -> volatile (simplified fix)')
