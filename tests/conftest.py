"""Test configuration — adds project root to sys.path so ``pipeline.*``
imports resolve when pytest runs from any cwd (e.g. CI in a worktree).
"""

import sys
from pathlib import Path

# Project root = parent of this tests/ directory
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
