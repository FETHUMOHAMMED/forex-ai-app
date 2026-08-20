"""Fix the stats import in proper_validation.py."""
from pathlib import Path

# Read the file
file_path = Path("tools/proper_validation.py")
content = file_path.read_text()

# Fix the stats import issue
content = content.replace(
    "from scipy import stats",
    "import scipy.stats as stats"
)

# Write back
file_path.write_text(content)
print("Fixed stats import")
