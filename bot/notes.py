"""Shim for backward compatibility — code moved to src/personalkm/.

This shim works both with and without ``pip install -e .`` . When the
editable install is not active (e.g. Mac Mini launchd using /usr/bin/python3),
it adds the ``src/`` directory to sys.path so ``from personalkm.xxx import YYY``
resolves correctly.
"""

from __future__ import annotations
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent  # bot/
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from personalkm.capture.notes import *  # noqa: F401, F403
