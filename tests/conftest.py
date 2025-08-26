import sys
from pathlib import Path


# Ensure the repository root is on sys.path so tests can import top-level modules
# This helps CI environments where pytest is invoked with a different working dir
# or where the project is not installed into the environment.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
