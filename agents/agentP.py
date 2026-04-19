"""
agentP.py — 60-Word Summary Generator
Generates a ≤60-word extractive summary for each article.

Strategy:
  1. Tries to fetch full article text via newspaper3k (if installed)
  2. Falls back to the stored full_text / RSS description
  3. Scores sentences by keyword frequency (TF-based)
  4. Joins top sentences until ≤60 words, ending on a complete sentence
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_pending_summary, update_article
import re

import requests as _requests, os as _os, time as _time

_GROQ_KEY   = _os.environ.get("GROQ_API_KEY", "")
_GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.1-8b-instant"
_last_call  = 0

def groq_call(prompt, max_tokens=120):
    global _last_call
    if not _GROQ_KEY: return ""
    gap = 2.5 - (_time.time() - _last_call)
    if gap > 0: _time.sleep(gap)
    _last_call = _time.time()
    try:
        r = _requests.post(_GROQ_URL,
            headers={"Authorization": f"Bearer {_GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": _GROQ_MODEL, "max_tokens": max_tokens, "temperature": 0.2,
                  "messages": [{"role": "user", "content": prompt}]}, timeout=15)
        if r.status_code == 429: _time.sleep(65); return ""
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠ Groq error: {e}"); return ""


import requests as _requests, os as _os, time as _time

_GROQ_KEY   = _os.environ.get("GROQ_API_KEY", "")
_GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.1-8b-instant"
_last_call  = 0

def groq_call(prompt, max_tokens=120):
    global _last_call
    if not _GROQ_KEY: return ""
    gap = 2.5 - (_time.time() - _last_call)
    if gap > 0: _time.sleep(gap)
    _last_call = _time.time()
    try:
        r = _requests.post(_GROQ_URL,
            headers={"Authorization": f"Bearer {_GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": _GROQ_MODEL, "max_tokens": max_tokens, "temperature": 0.2,
                  "messages": [{"role": "user", "content": prompt}]}, timeout=15)
        if r.status_code == 429: _time.sleep(65); return ""
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠ Groq error: {e}"); return ""


MAX_WORDS = 60

# ── Text extraction ──────────────────────────────────────────────────────────

def fetch_full_text(url: str) -> str:
    """Try newspaper3k → trafilatura → nothing."""
    if not url:
        return ''
    try:
        from newspaper import Article
        art = Article(url)
        art.download()
        art.parse()
        return art.text[:5000] if art.text else ''
    except Exception:
        pass
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        result = trafilatura.extract(downloaded)
        return (result or '')[:5000]
    except Exception:
        pass
    return ''


# ── Sentence tokeniser ────────────────────────────────────────────────────────

def split_sentences(text: str) -> list:
    """Split text into sentences, cleaning whitespace."""
    text = re.sub(r'\s+', ' ', text.strip())
    # Split on .!? followed by space + capital
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in parts if len(s.strip()) > 20]


# ── Extractive scoring ────────────────────────────────────────────────────────

STOPWORDS = {
    'the','a','an','is','are','was','were','be','been','being',
    'have','has','had','do','does','did','will','would','could','should',
    'in','on','at','to','for','of','and','or','but','with','from','by',
    'this','that','these','those','it','its','as','up','down',
}

def word_freq(sentences: list) -> dict:
    freq = {}
    for sent in sentences:
        for word in re.findall(r'\b[a-z]{3,}\b', sent.lower()):
            if word not in STOPWORDS:
                freq[word] = freq.get(word, 0) + 1
    # normalise
    if freq:
        max_f = max(freq.values())
        return {w: f / max_f for w, f in freq.items()}
    return freq

def score_sentence(sent: str, freq: dict) -> float:
    words = re.findall(r'\b[a-z]{3,}\b', sent.lower())
    if not words:
        return 0.0
    return sum(freq.get(w, 0) for w in words) / len(words)

def extractive_summary(text: str, title: str = '') -> str:
    """Return ≤MAX_WORDS word extractive summary."""
    sentences = split_sentences(text)
    if not sentences:
        # Nothing to work with — truncate title at MAX_WORDS
        words = (title or '').split()
        return ' '.join(words[:MAX_WORDS]) + ('...' if len(words) > MAX_WORDS else '')

    freq  = word_freq(sentences)
    scored = sorted(
        enumerate(sentences),
        key=lambda x: score_sentence(x[1], freq),
        reverse=True
    )

    # Pick top sentences in their original order until we hit MAX_WORDS
    chosen_indices = set()
    word_count = 0
    for idx, sent in scored:
        sent_words = len(sent.split())
        if word_count + sent_words > MAX_WORDS:
            continue
        chosen_indices.add(idx)
        word_count += sent_words
        if word_count >= MAX_WORDS * 0.8:
            break

    if not chosen_indices:
        # Fallback: just take the first sentence, truncated
        first = sentences[0].split()
        return ' '.join(first[:MAX_WORDS]) + ('...' if len(first) > MAX_WORDS else '')

    # Re-order chosen sentences by original position
    result_sentences = [sentences[i] for i in sorted(chosen_indices)]
    summary = ' '.join(result_sentences)

    # Hard-cap at MAX_WORDS
    words = summary.split()
    if len(words) > MAX_WORDS:
        summary = ' '.join(words[:MAX_WORDS]) + '...'

    return summary.strip()


# ── Main ──────────────────────────────────────────────────────────────────────

def run(limit: int = 300, fetch_online: bool = False) -> int:
    """
    fetch_online=True  → tries to download full article text (slower but richer)
    fetch_online=False → uses stored full_text / RSS description only (fast)
    """
    print(f"📝 AgentP — 60-Word Summariser  [fetch_online={fetch_online}]")
    articles = get_pending_summary(limit)

    if not articles:
        print("  ℹ  Nothing to summarise.\n")
        return 0

    processed = 0
    for art in articles:
        title    = art.get('title', '') or ''
        stored   = art.get('full_text', '') or ''
        url      = art.get('url', '')

        # Prefer fetched full text if requested and stored text is thin
        text = stored
        if fetch_online and len(stored.split()) < 40:
            online = fetch_full_text(url)
            if online:
                text = online

        if not text:
            text = title   # last resort

        # Try Groq first for AI summary
        summary = ""
        if _GROQ_KEY and (title or text):
            prompt = f"""Summarise this financial news in exactly 60 words or fewer.
Be factual, mention company names, numbers, and market impact. No fluff. Write only the summary.
Article: {title}
{text[:800]}"""
            summary = groq_call(prompt, max_tokens=100)

        # Fallback to extractive if Groq failed
        if not summary:
            # Try Groq first for AI summary
        summary = ""
        if _GROQ_KEY and (title or text):
            prompt = (
                "Summarise this financial news in exactly 60 words or fewer. "
                "Be factual, mention company names, numbers, and market impact. No fluff. Write only the summary.\n"
                f"Article: {title}\n{text[:800]}"
            )
            summary = groq_call(prompt, max_tokens=100)

        # Fallback to extractive if Groq failed
        if not summary:
            summary = extractive_summary(text, title)

        update_article(art['id'], {'summary_60w': summary})
        processed += 1

    print(f"  ✅ AgentP summarised {processed} articles\n")
    return processed


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--fetch-online', action='store_true',
                   help='Download full article text before summarising')
    args = p.parse_args()
    run(fetch_online=args.fetch_online)
