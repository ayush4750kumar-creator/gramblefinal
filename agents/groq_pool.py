"""
groq_pool.py — Thread-safe Groq API key pool with round-robin rotation.

Two independent pools:
  - MAIN_POOL   → used by run_once() (main pipeline, 8 keys)
  - SEARCH_POOL → used by run_for_symbol() (search pipeline, 3 keys)

They never share keys so searching never slows down the main pipeline.
"""
import os
import time
import threading


class GroqKeyPool:
    def __init__(self, keys: list):
        assert keys, "GroqKeyPool needs at least one key"
        self._keys  = keys
        self._index = 0
        self._lock  = threading.Lock()

    def next_key(self) -> str:
        with self._lock:
            key = self._keys[self._index % len(self._keys)]
            self._index += 1
            return key

    def __len__(self):
        return len(self._keys)

    def __repr__(self):
        return f"GroqKeyPool({len(self._keys)} keys)"


def _load_main() -> list:
    """Load main pool keys from GROQ_API_KEY_1 … GROQ_API_KEY_8."""
    keys = []
    for i in range(1, 9):
        val = os.getenv(f"GROQ_API_KEY_{i}", "").strip()
        if val:
            keys.append(val)
    if not keys:
        single = os.getenv("GROQ_API_KEY", "").strip()
        if single:
            keys.append(single)
    if not keys:
        print("⚠  WARNING: No keys found for MAIN_POOL (GROQ_API_KEY_1 … GROQ_API_KEY_8)")
    return keys


def _load(env_var: str) -> list:
    """Load comma-separated API keys from an env variable."""
    raw = os.getenv(env_var, "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        print(f"⚠  WARNING: No keys found in env var '{env_var}'")
    return keys


# ── Two independent pools ─────────────────────────────────────────────────────

MAIN_POOL   = GroqKeyPool(_load_main() or ["placeholder"])
SEARCH_POOL = GroqKeyPool(_load("GROQ_SEARCH_API_KEYS") or ["placeholder"])


# ── Helper: call Groq with auto-retry across keys on rate limit ───────────────

def call_with_pool(pool: GroqKeyPool, fn, retries: int = 3):
    last_error = None
    for attempt in range(retries):
        api_key = pool.next_key()
        try:
            return fn(api_key)
        except Exception as e:
            err_str = str(e).lower()
            if "rate limit" in err_str or "429" in err_str:
                wait = 2 ** attempt
                print(f"⚠  Rate limit on key ...{api_key[-6:]}, retrying in {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                last_error = e
            else:
                raise
    raise RuntimeError(f"All {retries} retries exhausted. Last error: {last_error}")