"""Verify Machine-Readable Result matches advisor's exact specification"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.integrity.machine_readable import run_full_scanner

# Run scanner and get result
result = run_full_scanner()

print("=" * 70)
print("  MACHINE-READABLE RESULT - ADVISOR VERIFICATION")
print("=" * 70)

# Advisor's required fields
required_fields = ["system", "timestamp", "overall", "trading_allowed", 
                   "domains", "critical_errors"]

print("\n  REQUIRED FIELDS:")
all_fields_present = True
for field in required_fields:
    present = field in result
    if not present:
        all_fields_present = False
    icon = "PRESENT" if present else "MISSING"
    print(f"  [{icon}] {field}")

# Verify system name
print(f"\n  SYSTEM NAME:")
print(f"  Value: {result.get('system')}")
print(f"  Expected: FOREX-AI-APP")
print(f"  Match: {result.get('system') == 'FOREX-AI-APP'}")

# Verify timestamp format
print(f"\n  TIMESTAMP:")
print(f"  Value: {result.get('timestamp')}")
print(f"  Is ISO8601 with timezone: {'+' in str(result.get('timestamp', '')) or 'Z' in str(result.get('timestamp', ''))}")

# Verify overall is one of 3 states
print(f"\n  OVERALL STATE:")
overall = result.get('overall')
valid_states = ['READY', 'DEGRADED', 'HALT']
print(f"  Value: {overall}")
print(f"  Valid: {overall in valid_states}")

# Verify trading_allowed is boolean
print(f"\n  TRADING_ALLOWED:")
ta = result.get('trading_allowed')
print(f"  Value: {ta}")
print(f"  Is boolean: {isinstance(ta, bool)}")
print(f"  Matches HALT: {ta == (overall != 'HALT')}")

# Verify domains format
print(f"\n  DOMAINS:")
domains = result.get('domains', {})
print(f"  Count: {len(domains)}")
for domain, state in domains.items():
    valid_domain_states = ['PASS', 'FAIL', 'DEGRADED']
    icon = "OK" if state in valid_domain_states else "INVALID"
    print(f"    {domain}: {state} [{icon}]")

# Verify critical_errors format
print(f"\n  CRITICAL ERRORS:")
criticals = result.get('critical_errors', [])
print(f"  Count: {len(criticals)}")
for err in criticals[:3]:
    has_code = 'code' in err
    has_severity = 'severity' in err
    icon = "OK" if has_code and has_severity else "MISSING FIELDS"
    print(f"    {err.get('code', 'N/A')}: {err.get('severity', 'N/A')} [{icon}]")

# Verify JSON serializable
print(f"\n  JSON SERIALIZABLE:")
try:
    json_str = json.dumps(result)
    print(f"  PASS - {len(json_str)} bytes")
except Exception as e:
    print(f"  FAIL - {e}")

# Verify saved to file
saved_file = Path("ai-service/scanner_result.json")
print(f"\n  SAVED TO FILE:")
print(f"  {saved_file}")
print(f"  Exists: {saved_file.exists()}")

print(f"\n{'='*70}")
checks_pass = (
    all_fields_present and 
    result.get('system') == 'FOREX-AI-APP' and 
    overall in valid_states and
    isinstance(ta, bool) and
    saved_file.exists()
)
print(f"  VERDICT: {'MACHINE-READABLE RESULT COMPLETE' if checks_pass else 'ISSUES FOUND'}")
print("=" * 70)
