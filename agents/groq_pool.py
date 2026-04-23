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
        """Returns the next key in round-robin order. Thread-safe."""
        with self._lock:
            key = self._keys[self._index % len(self._keys)]
            self._index += 1
            return key

    def __len__(self):
        return len(self._keys)

    def __repr__(self):
        return f"GroqKeyPool({len(self._keys)} keys)"


def _load(env_var: str) -> list:
    """Load comma-separated API keys from an env variable."""
    raw = os.getenv(env_var, "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        print(f"⚠  WARNING: No keys found in env var '{env_var}'")
    return keys


# ── Two independent pools ─────────────────────────────────────────────────────

# Main pipeline pool — fed by GROQ_API_KEYS (your existing 8 keys)
MAIN_POOL = GroqKeyPool(_load("GROQ_API_KEYS") or ["placeholder"])

# Search pipeline pool — fed by GROQ_SEARCH_API_KEYS (your 3 new keys)
SEARCH_POOL = GroqKeyPool(_load("GROQ_SEARCH_API_KEYS") or ["placeholder"])


# ── Helper: call Groq with auto-retry across keys on rate limit ───────────────

def call_with_pool(pool: GroqKeyPool, fn, retries: int = 3):
    """
    Calls fn(api_key) rotating to the next key on rate limit errors.

    Usage:
        result = call_with_pool(SEARCH_POOL, lambda key:
            groq.Client(api_key=key).chat.completions.create(...)
        )
    """
    last_error = None
    for attempt in range(retries):
        api_key = pool.next_key()
        try:
            return fn(api_key)
        except Exception as e:
            err_str = str(e).lower()
            if "rate limit" in err_str or "429" in err_str:
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"⚠  Rate limit on key ...{api_key[-6:]}, retrying in {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                last_error = e
            else:
                raise  # non-rate-limit errors bubble up immediately
    raise RuntimeError(f"All {retries} retries exhausted. Last error: {last_error}")