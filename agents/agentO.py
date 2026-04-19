"""
agentO.py — Market Sentiment Analyser
Reads each article and assigns:
  • sentiment_label  → 'bullish' | 'bearish' | 'neutral'
  • sentiment_reason → one-line explanation

Uses a weighted keyword scoring model — no external API keys required.
Can optionally use VADER if installed: pip install vaderSentiment
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_pending_sentiment, update_article
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

# Reason templates
REASON_TEMPLATES = {
    ('bullish', 'strong'):   "Strong positive signal: {word} detected in article.",
    ('bullish', 'moderate'): "Positive tone: {word} suggests upward movement.",
    ('bearish', 'strong'):   "Strong negative signal: {word} detected in article.",
    ('bearish', 'moderate'): "Negative tone: {word} suggests downward pressure.",
    ('neutral', ''):         "No dominant bullish or bearish signals found.",
}


def tokenise(text: str) -> list:
    return re.sub(r'[^a-z\s\-]', '', (text or '').lower()).split()


def score_text(tokens: list) -> tuple:
    """
    Returns (score: float, trigger_word: str, intensity: str)
    score > 0 = bullish, score < 0 = bearish
    """
    bull_score = 0.0
    bear_score = 0.0
    trigger_bull = ''
    trigger_bear = ''

    for i, tok in enumerate(tokens):
        # check for negation in window of 3 words before
        negated = any(tokens[max(0, i-3):i][j] in NEGATION_WORDS
                      for j in range(len(tokens[max(0, i-3):i])))

        # bigram check too
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
        return net, trigger_bull or 'positive momentum', intensity, 'bullish'
    elif net < -1.5:
        intensity = 'strong' if net < -4.0 else 'moderate'
        return net, trigger_bear or 'negative momentum', intensity, 'bearish'
    else:
        return net, '', '', 'neutral'


def try_vader(text: str):
    """Optional VADER fallback — returns (label, reason) or None."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyser = SentimentIntensityAnalyzer()
        score = analyser.polarity_scores(text)
        compound = score['compound']
        if compound >= 0.05:
            return 'bullish', f"VADER compound score: {compound:.2f} (positive)"
        elif compound <= -0.05:
            return 'bearish', f"VADER compound score: {compound:.2f} (negative)"
        else:
            return 'neutral', f"VADER compound score: {compound:.2f} (neutral)"
    except ImportError:
        return None


def analyse_article(title: str, text: str) -> tuple:
    """Returns (label, reason) — uses Groq if available, else keyword fallback."""
    combined = (title or '') + ' ' + (text or '')[:800]

    if _GROQ_KEY:
        prompt = f"""You are a financial analyst. Read this news and respond with ONLY a JSON object.
Article: {combined[:600]}
Respond exactly: {{"sentiment": "bullish" or "bearish" or "neutral", "reason": "one sentence max 20 words explaining why"}}"""
        raw = groq_call(prompt, max_tokens=80)
        if raw:
            try:
                import json
                clean = raw.replace("```json","").replace("```","").strip()
                start, end = clean.find("{"), clean.rfind("}")+1
                if start >= 0 and end > start:
                    data = json.loads(clean[start:end])
                    label = data.get("sentiment","neutral").lower()
                    if label not in ("bullish","bearish","neutral"): label = "neutral"
                    return label, data.get("reason","")
            except: pass

    # Fallback: keyword scoring
    tokens = tokenise(combined)
    _, trigger, intensity, label = score_text(tokens)
    if label == 'neutral':
        reason = REASON_TEMPLATES[('neutral', '')]
    else:
        template = REASON_TEMPLATES.get((label, intensity), "{word} trend detected.")
        reason = template.format(word=trigger)
    return label, reason


def run(limit: int = 300) -> int:
    print("📊 AgentO — Sentiment Analyser")
    articles = get_pending_sentiment(limit)

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
            # also write to existing 'sentiment' column if it exists (▲/▼)
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
