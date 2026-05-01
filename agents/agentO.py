"""
agentO.py — Market Sentiment Analyser
Reads each article and assigns:
  • sentiment_label  → 'bullish' | 'bearish' | 'neutral'
  • sentiment_reason → one-line explanation of what the article contains

Uses a weighted keyword scoring model — no external API keys required.
Can optionally use VADER if installed: pip install vaderSentiment
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_pending_sentiment, update_article
import re
import requests as _requests, time as _time

_GROQ_KEY   = os.environ.get("GROQ_API_KEY", "")
_GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.1-8b-instant"
_last_call  = 0


def groq_call(prompt, max_tokens=80):
    global _last_call
    if not _GROQ_KEY: return ""
    gap = 2.5 - (_time.time() - _last_call)
    if gap > 0: _time.sleep(gap)
    _last_call = _time.time()
    try:
        r = _requests.post(_GROQ_URL,
            headers={"Authorization": f"Bearer {_GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": _GROQ_MODEL, "max_tokens": max_tokens, "temperature": 0.0,
                  "messages": [{"role": "user", "content": prompt}]}, timeout=15)
        if r.status_code == 429: _time.sleep(65); return ""
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠ Groq error: {e}"); return ""


# ── Sentiment lexicon ─────────────────────────────────────────────────────────

BULLISH_STRONG = {
    'surges', 'soars', 'skyrockets', 'record high', 'all-time high',
    'blowout', 'blowout earnings', 'beats expectations', 'upgrade', 'upgraded',
    'strong buy', 'outperform', 'overweight', 'buy rating',
    'profit up', 'revenue up', 'growth', 'rally', 'breakout',
    'acquisition', 'merger approved', 'dividend hike', 'buyback',
    'market share gain', 'positive outlook', 'raises guidance', 'bullish',
    'bull case', 'recovery', 'rebound', 'momentum', 'strong demand',
}

BULLISH_MODERATE = {
    'gains', 'rises', 'increases', 'higher', 'up', 'positive',
    'beats', 'better than expected', 'in-line', 'solid', 'strong',
    'outperforms', 'leads', 'expanding', 'growing', 'improving',
    'new contract', 'new order', 'partnership', 'collaboration',
    'launches', 'expands', 'invest', 'capex',
}

BEARISH_STRONG = {
    'crashes', 'collapses', 'plunges', 'all-time low', '52-week low',
    'misses expectations', 'profit warning', 'earnings miss',
    'downgrade', 'downgraded', 'sell', 'underperform', 'underweight',
    'loss widens', 'revenue falls', 'guidance cut', 'bearish',
    'bear case', 'bankruptcy', 'default', 'fraud', 'scam', 'penalty',
    'sebi action', 'rbi action', 'regulatory probe', 'investigation',
    'layoffs', 'job cuts', 'downsizing', 'plant closure',
}

BEARISH_MODERATE = {
    'falls', 'drops', 'declines', 'lower', 'down', 'negative',
    'misses', 'below expectations', 'weak', 'disappoints', 'slows',
    'contracts', 'shrinks', 'uncertainty', 'concerns', 'risks',
    'pressure', 'headwinds', 'challenges', 'volatile',
}

NEGATION_WORDS = {'not', "n't", 'no', 'never', 'neither', 'without', 'barely', 'hardly'}


def tokenise(text: str) -> list:
    return re.sub(r'[^a-z\s\-]', '', (text or '').lower()).split()


def score_text(tokens: list) -> tuple:
    """
    Returns (score: float, trigger_word: str, intensity: str, label: str)
    score > 0 = bullish, score < 0 = bearish
    """
    bull_score = 0.0
    bear_score = 0.0
    trigger_bull = ''
    trigger_bear = ''

    for i, tok in enumerate(tokens):
        negated = any(tokens[max(0, i-3):i][j] in NEGATION_WORDS
                      for j in range(len(tokens[max(0, i-3):i])))
        bigram = tok + (' ' + tokens[i+1] if i+1 < len(tokens) else '')

        for phrase in list(BULLISH_STRONG) + list(BULLISH_MODERATE):
            if phrase in tok or phrase in bigram:
                weight = 2.0 if phrase in BULLISH_STRONG else 1.0
                if negated:
                    bear_score += weight * 0.5
                else:
                    bull_score += weight
                    if not trigger_bull:
                        trigger_bull = phrase

        for phrase in list(BEARISH_STRONG) + list(BEARISH_MODERATE):
            if phrase in tok or phrase in bigram:
                weight = 2.0 if phrase in BEARISH_STRONG else 1.0
                if negated:
                    bull_score += weight * 0.5
                else:
                    bear_score += weight
                    if not trigger_bear:
                        trigger_bear = phrase

    net = bull_score - bear_score
    if net > 1.5:
        intensity = 'strong' if net > 4.0 else 'moderate'
        return net, trigger_bull or 'positive indicators', intensity, 'bullish'
    elif net < -1.5:
        intensity = 'strong' if net < -4.0 else 'moderate'
        return net, trigger_bear or 'negative indicators', intensity, 'bearish'
    else:
        return net, '', '', 'neutral'


def build_reason(label: str, intensity: str, trigger: str, title: str) -> str:
    """
    Build a factual one-line reason that describes what the article reports,
    not what might happen to the stock or investors.
    """
    if label == 'neutral':
        return "Article contains no dominant bullish or bearish signals."

    # Use the article title to make the reason specific and factual
    title_short = title.strip().rstrip('.') if title else ''

    if label == 'bullish':
        if intensity == 'strong':
            return f"Article reports {trigger} — a strongly positive development."
        else:
            return f"Article reports {trigger} — a positive development."
    else:  # bearish
        if intensity == 'strong':
            return f"Article reports {trigger} — a strongly negative development."
        else:
            return f"Article reports {trigger} — a negative development."


def analyse_article_groq(title: str, text: str) -> tuple:
    """
    Use Groq to classify sentiment with a factual reason.
    Returns (label, reason) or ("", "") on failure.
    """
    combined = (title or '') + ' ' + (text or '')[:600]
    prompt = (
        "You are a financial news classifier. Read this article and return ONLY a JSON object.\n"
        "Classify the sentiment as bullish, bearish, or neutral based strictly on what the article reports.\n"
        "The reason must describe what the article says — not predict stock moves or investor reactions.\n"
        "Bad reason: 'Company X may see a rally.' "
        "Good reason: 'Company X reported a 20% rise in quarterly profit.'\n"
        f"Article: {combined}\n"
        'Respond ONLY with: {"sentiment": "bullish" or "bearish" or "neutral", '
        '"reason": "one sentence describing what the article reports, max 20 words"}'
    )
    raw = groq_call(prompt, max_tokens=80)
    if not raw:
        return "", ""
    try:
        import json
        clean = raw.replace("```json", "").replace("```", "").strip()
        start, end = clean.find("{"), clean.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(clean[start:end])
            label = data.get("sentiment", "neutral").lower()
            if label not in ("bullish", "bearish", "neutral"):
                label = "neutral"
            reason = data.get("reason", "").strip()
            return label, reason
    except Exception:
        pass
    return "", ""


def analyse_article(title: str, text: str) -> tuple:
    """Returns (label, reason)."""
    # Try Groq first if key is available
    if _GROQ_KEY:
        label, reason = analyse_article_groq(title, text)
        if label:
            return label, reason

    # Fallback: keyword scoring
    combined = (title or '') + ' ' + (text or '')[:800]
    tokens = tokenise(combined)
    _, trigger, intensity, label = score_text(tokens)
    reason = build_reason(label, intensity, trigger, title)
    return label, reason


def run(limit: int = 20) -> int:
    print("📊 AgentO — Sentiment Analyser")
    try:
        articles = get_pending_sentiment(limit)
    except Exception as e:
        print(f"  ❌ AgentO DB error: {e}")
        return 0

    if not articles:
        print("  ℹ  Nothing to analyse.\n")
        return 0

    counts = {'bullish': 0, 'bearish': 0, 'neutral': 0}

    for art in articles:
        title  = art.get('title', '') or ''
        text   = art.get('full_text', '') or ''
        label, reason = analyse_article(title, text)

        update_article(art['id'], {
            'sentiment_label':  label,
            'sentiment_reason': reason,
        })
        counts[label] += 1

    total = sum(counts.values())
    print(
        f"  ✅ AgentO analysed {total}: "
        f"🟢 bullish {counts['bullish']} | "
        f"🔴 bearish {counts['bearish']} | "
        f"⚪ neutral {counts['neutral']}\n"
    )
    return total


if __name__ == '__main__':
    run()