with open("ai-service/auto_trader_exness.py", "r", encoding="utf-8") as f:
    content = f.read()

old = """            except Exception as e:
                logger.debug(f"Trade scorer skipped: {e}")
                continue"""

new = """            except Exception as e:
                logger.warning(f"Trade scorer failed: {e} - using fallback quality")
                class FallbackQuality:
                    grade = "C"
                    total_score = 50
                    recommendation = "CAUTIOUS"
                    ml_score = 25
                    ict_score = 50
                    institutional_score = 50
                    trend_score = 50
                quality = FallbackQuality()"""

if old in content:
    content = content.replace(old, new)
    print("Replaced successfully")
else:
    print("OLD TEXT NOT FOUND - checking what's there:")
    # Find the except block
    for i, line in enumerate(content.split('\n')):
        if 'Trade scorer' in line:
            print(f"Line {i}: {line}")
            # Show surrounding lines
            start = max(0, i-2)
            end = min(len(content.split('\n')), i+5)
            for j in range(start, end):
                print(f"  {j}: {content.split(chr(10))[j]}")

with open("ai-service/auto_trader_exness.py", "w", encoding="utf-8") as f:
    f.write(content)
