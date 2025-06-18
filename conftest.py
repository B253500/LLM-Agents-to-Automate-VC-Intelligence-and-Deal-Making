# conftest.py
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
if str(root) not in sys.path:  # idempotent
    sys.path.insert(0, str(root))
