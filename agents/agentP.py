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
            json={"model": _GROQ_MODEL, "max_tokens": max_tokens, "temperature": 0.2,
                  "messages": [{"role": "user", "content": prompt}]}, timeout=15)
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
    Never truncates mid-sentence — if a sentence would exceed the limit,
    it is skipped in favour of a shorter one. The result always ends on a
    complete sentence boundary.
    """
    sentences = split_sentences(text)
    if not sentences:
        # Fall back to title, but still end on a word boundary — no mid-word cut
        words = (title or '').split()
        return ' '.join(words[:MAX_WORDS])

    freq = word_freq(sentences)
    scored = sorted(enumerate(sentences), key=lambda x: score_sentence(x[1], freq), reverse=True)

    chosen_indices = set()
    word_count = 0
    for idx, sent in scored:
        sent_words = len(sent.split())
        # Only include this sentence if it fits entirely within the word budget
        if word_count + sent_words > MAX_WORDS:
            continue
        chosen_indices.add(idx)
        word_count += sent_words
        if word_count >= MAX_WORDS * 0.8:
            break

    if not chosen_indices:
        # Even the shortest relevant sentence is too long — take the first sentence as-is
        # (it is already a complete sentence, just long)
        return sentences[0]

    # Re-assemble in original reading order
    result_sentences = [sentences[i] for i in sorted(chosen_indices)]
    summary = ' '.join(result_sentences)
    return summary.strip()

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
            # Prompt instructs the model to report facts only — no predictions,
            # no sentiment, no market-impact speculation.
            prompt = (
                "Summarise this financial news article in 60 words or fewer. "
                "Report only what happened: the facts, the people or companies involved, "
                "and any figures or decisions mentioned. "
                "Do NOT predict stock moves, investor reactions, or market impact. "
                "Do NOT use phrases like 'is expected to', 'may', 'could boost', "
                "'investors optimistic', or any forward-looking language. "
                "End with a complete sentence — never cut off mid-thought. "
                "Write only the summary, no preamble.\n"
                f"Article: {title}\n{text[:800]}"
            )
            summary = groq_call(prompt, max_tokens=100)
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