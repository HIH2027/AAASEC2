"""Vercel entry point.

Vercel's Python builder discovers an ASGI application here and serves it
on every path. Routing stays inside Starlette, so no rewrite is needed --
a rewrite would replace the request path and break every route.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from medication_safety.web import app  # noqa: E402

__all__ = ["app"]
