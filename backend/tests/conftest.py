"""Shared test setup.

The agent modules build a module-level `Groq(api_key=...)` client at import
time, which raises immediately if no API key is present in the environment -
so a dummy key has to exist *before* any `agents.*` module is imported.
Tracing is left off (the codebase's own default) so `@traceable` calls never
try to reach the network during a test run.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("GROQ_API_KEY", "test-dummy-key")
os.environ.setdefault("LANGSMITH_TRACING", "false")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
