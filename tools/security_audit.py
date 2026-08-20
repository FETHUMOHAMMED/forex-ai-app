"""Security Audit - Find hardcoded secrets and vulnerabilities"""
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(".")

# Patterns that suggest hardcoded secrets
SECRET_PATTERNS = [
    (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded password'),
    (r'token\s*=\s*["\'][^"\']{10,}["\']', 'Hardcoded token'),
    (r'api_key\s*=\s*["\'][^"\']{10,}["\']', 'Hardcoded API key'),
    (r'secret\s*=\s*["\'][^"\']{10,}["\']', 'Hardcoded secret'),
    (r'chat_id\s*=\s*["\']\d+["\']', 'Hardcoded chat ID'),
    (r'webhook.*=.*["\']https?://[^"\']+["\']', 'Hardcoded webhook URL'),
    (r'\d{8,10}\s*#.*account', 'Potential account ID in comment'),
    (r'bot\d+:[A-Za-z0-9_-]{35,}', 'Telegram bot token pattern'),
]

SKIP_DIRS = {'.venv', 'node_modules', '__pycache__', '.git', 'archive', 
             'venv', 'scripts/venv', 'frontend/node_modules', 'backend/node_modules'}

print("=" * 60)
print("  SECURITY AUDIT")
print("=" * 60)

issues_found = 0

for py_file in PROJECT_ROOT.rglob("*.py"):
    # Skip excluded directories
    parts = set(py_file.parts)
    if parts & SKIP_DIRS:
        continue
    
    try:
        with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line_no, line in enumerate(lines, 1):
            for pattern, issue_type in SECRET_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip if it uses os.getenv or environment variable
                    if 'os.getenv' in line or 'os.environ' in line or 'getenv' in line:
                        continue
                    if 'CONFIG.get' in line or 'config[' in line.lower():
                        continue
                    
                    issues_found += 1
                    print(f"\n  [{issue_type}]")
                    print(f"  File: {py_file}:{line_no}")
                    # Mask the actual value
                    masked = re.sub(r'["\']([^"\']{4})[^"\']*([^"\']{4})["\']', r'"\1****\2"', line.strip())
                    print(f"  Line: {masked}")
    except:
        pass

# Check for .env file
env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    print(f"\n  [INFO] .env file exists - good for local secrets")
else:
    print(f"\n  [WARNING] No .env file found")

# Check .gitignore for sensitive patterns
gitignore = PROJECT_ROOT / ".gitignore"
if gitignore.exists():
    with open(gitignore, 'r') as f:
        content = f.read()
    required = ['.env', '*.key', '*.pem', 'credentials*', 'secrets*']
    missing = [r for r in required if r not in content]
    if missing:
        print(f"\n  [WARNING] .gitignore missing patterns: {missing}")
    else:
        print(f"\n  [OK] .gitignore protects sensitive files")

print(f"\n{'='*60}")
print(f"  Total issues found: {issues_found}")
print(f"{'='*60}")
