import sys
from pathlib import Path


# Put repository root on sys.path so tests can import top-level modules like
# `database` and generated protobuf modules regardless of the pytest CWD.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
