"""Vercel entry point.

Vercel serves the Starlette app as a single Python function. Static files are
served by Starlette itself so the deployment needs no separate build step.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from medication_safety.web import app  # noqa: E402

__all__ = ["app"]
