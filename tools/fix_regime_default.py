# When predictor fails, default to 'volatile' instead of rejecting
content = open('ai-service/auto_trader_exness.py', encoding='utf-8', errors='replace').read()

old = '''                    except Exception as e:
                        logger.info(f"REJECTED {pair}: UNKNOWN regime, predictor failed: {e} (acc={acc.name})")
                        self.rejection_counts['regime'] = self.rejection_counts.get('regime', 0) + 1
                        continue'''

new = '''                    except Exception as e:
                        # Predictor failed - default to volatile (safe default)
                        regime = 'volatile'
                        signal['regime'] = 'volatile'
                        print(f"[REGIME FALLBACK] {pair}: predictor failed ({e}), defaulting to volatile")'''

content = content.replace(old, new)
open('ai-service/auto_trader_exness.py', 'w', encoding='utf-8').write(content)
print('Fixed: predictor failure defaults to volatile instead of rejecting')
