"""
agentP.py — 60-Word Summary Generator (Groq-powered)
"""
import sys, os, re, requests, time
sys.path.insert(0, os.path.dirname(__file__))
from db_utils import get_pending_summary, update_article

MAX_WORDS = 60
_GROQ_KEY   = os.environ.get("GROQ_API_KEY", "")
_GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.1-8b-instant"
_last_call  = 0

SYSTEM_PROMPT = (
    "You are a financial news summariser. Your only job is to compress an article "
    "into the key facts it actually states. "
    "STRICT RULES — violating any of these is failure:\n"
    "1. Only include facts explicitly stated in the article.\n"
    "2. NEVER write predictions, forecasts, or market impact — not even hedged ones.\n"
    "3. NEVER use: 'expected to', 'may', 'could', 'likely', 'might', 'would boost', "
    "'investors optimistic', 'positive impact', 'negative impact', or any similar phrase.\n"
    "4. NEVER add a concluding sentence that wasn't in the article.\n"
    "5. End on a complete sentence. Never cut off mid-thought.\n"
    "6. Maximum 60 words. Write ONLY the summary — no preamble, no label."
)

def groq_call(prompt, max_tokens=120):
    global _last_call
    if not _GROQ_KEY:
        return ""
    gap = 2.5 - (time.time() - _last_call)
    if gap > 0:
        time.sleep(gap)
    _last_call = time.time()
    try:
        r = requests.post(_GROQ_URL,
            headers={"Authorization": f"Bearer {_GROQ_KEY}", "Content-Type": "application/json"},
            json={
                "model": _GROQ_MODEL,
                "max_tokens": max_tokens,
                "temperature": 0.0,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            }, timeout=15)
        if r.status_code == 429:
            time.sleep(65)
            return ""
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠ Groq error: {e}")
        return ""

STOPWORDS = {
    'the','a','an','is','are','was','were','be','been','being',
    'have','has','had','do','does','did','will','would','could','should',
    'in','on','at','to','for','of','and','or','but','with','from','by',
    'this','that','these','those','it','its','as','up','down',
}

def split_sentences(text):
    text = re.sub(r'\s+', ' ', text.strip())
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in parts if len(s.strip()) > 20]

def word_freq(sentences):
    freq = {}
    for sent in sentences:
        for word in re.findall(r'\b[a-z]{3,}\b', sent.lower()):
            if word not in STOPWORDS:
                freq[word] = freq.get(word, 0) + 1
    if freq:
        max_f = max(freq.values())
        return {w: f / max_f for w, f in freq.items()}
    return freq

def score_sentence(sent, freq):
    words = re.findall(r'\b[a-z]{3,}\b', sent.lower())
    if not words:
        return 0.0
    return sum(freq.get(w, 0) for w in words) / len(words)

def extractive_summary(text, title=''):
    """
    Select the most relevant complete sentences up to MAX_WORDS.
    Never truncates mid-sentence — skips sentences that don't fit entirely.
    """
    sentences = split_sentences(text)
    if not sentences:
        words = (title or '').split()
        return ' '.join(words[:MAX_WORDS])

    freq = word_freq(sentences)
    scored = sorted(enumerate(sentences), key=lambda x: score_sentence(x[1], freq), reverse=True)

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
        return sentences[0]

    result_sentences = [sentences[i] for i in sorted(chosen_indices)]
    return ' '.join(result_sentences).strip()

def run(limit=20, fetch_online=False):
    print(f"📝 AgentP — 60-Word Summariser [Groq={'on' if _GROQ_KEY else 'off'}]")
    articles = get_pending_summary(limit)
    if not articles:
        print("  ℹ  Nothing to summarise.\n")
        return 0
    processed = 0
    for art in articles:
        title = art.get('title', '') or ''
        text  = art.get('full_text', '') or ''
        description = art.get('description', '') or ''
        if not text:
            text = description or title
        summary = ""
        if _GROQ_KEY:
            prompt = (
                "Summarise the article below in 60 words or fewer. "
                "Only use facts from the article. "
                "BAD: 'This is expected to boost investor confidence.' "
                "GOOD: 'Profit rose 14% to ₹6.09bn. Revenue up 5.6%. NPA improved to 2.41%.'\n\n"
                f"Title: {title}\n"
                f"Article: {text[:1200]}"
            )
            summary = groq_call(prompt, max_tokens=110)
        if not summary:
            if text and text != title:
                summary = extractive_summary(text, title)
            else:
                summary = title
        update_article(art['id'], {'summary_60w': summary})
        processed += 1
    print(f"  ✅ AgentP summarised {processed} articles\n")
    return processed

if __name__ == '__main__':
    run()