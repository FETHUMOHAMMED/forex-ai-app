# Optimize the daemon cycle with parallel analysis, caching, and fast/slow loops

# 1. Find where pairs are analyzed sequentially
import re

with open("ai-service/ai_service_daemon.py", "r", encoding="utf-8") as f:
    content = f.read()

# Count current approach
if "ThreadPoolExecutor" in content or "asyncio.gather" in content:
    print("Already parallelized")
else:
    print("Currently sequential - needs parallelization")

# 2. Check MT5 data fetching
mt5_calls = content.count("copy_rates_from_pos")
print(f"MT5 copy_rates calls in code: {mt5_calls}")

# 3. Check for caching
has_cache = "cache" in content.lower() and ("signal" in content.lower() or "candle" in content.lower())
print(f"Has caching: {has_cache}")

print("\nOptimizations needed:")
print("1. Parallelize pair analysis with ThreadPoolExecutor")
print("2. Cache MT5 candles (only fetch new bars)")
print("3. Separate slow analysis loop from fast execution loop")
print("4. Skip ML if ICT already rejects")
print("5. Reduce logging level for production")
