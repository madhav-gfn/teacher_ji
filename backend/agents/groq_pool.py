"""
Round-robins Groq API calls across multiple keys.

A single teaching turn can easily be 4-6 Groq calls (Supervisor, the Learning
Agent's tool-calling loop, Reflection, and on a reflection retry, all of that
again) - on the free tier that saturates one key's rate limit fast. Configure
GROQ_API_KEYS as a comma-separated list to spread calls across several keys;
GROQ_API_KEY alone still works unchanged as a single-key setup.

next_client() is called once per individual API attempt (see
agents/subject_agents.py:call_groq_with_retry and _create_completion), not
once per turn - so a retry after a rate-limit error lands on a different key
automatically instead of immediately re-hitting the one that just 429'd.
"""
from __future__ import annotations

import itertools
import os

from groq import Groq


def _load_keys() -> list[str]:
    raw = os.environ.get("GROQ_API_KEYS", "")
    keys = [key.strip() for key in raw.split(",") if key.strip()]
    if keys:
        return keys
    single = os.environ.get("GROQ_API_KEY", "").strip()
    return [single] if single else []


_KEYS = _load_keys() or [""]  # empty key still constructs a client that fails clearly at call time
_CLIENTS = [Groq(api_key=key) for key in _KEYS]
_POOL = itertools.cycle(_CLIENTS)


def next_client() -> Groq:
    """Return the next client in rotation."""
    return next(_POOL)


def configured_key_count() -> int:
    return len(_KEYS)
