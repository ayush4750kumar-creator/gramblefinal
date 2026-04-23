"""
agentZ.py — Deduplicator
Compares recent articles pairwise using TF-IDF cosine similarity on title + summary.
If two articles score above the similarity threshold → marks the newer one as duplicate.
Keeps the one with the more authoritative source (based on priority list).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from db_utils import get_pending_dedup, mark_duplicate
import re
from math import log, sqrt
from collections import Counter

SOURCE_PRIORITY = [
    "sec edgar", "nse", "bse", "sebi", "rbi", "pib",
    "reuters", "bloomberg", "associated press", "ap news",
    "wall street journal", "financial times",
    "economic times", "moneycontrol", "livemint", "business standard",
    "cnbc", "ndtv", "yahoo finance",
]

SIMILARITY_THRESHOLD = 0.75

STOPWORDS = {
    'the','a','an','is','are','was','were','be','been','being',
    'have','has','had','do','does','did','will','would','could','should',
    'in','on','at','to','for','of','and','or','but','with','from','by',
    'this','that','these','those','it','its','as','up','down','over',
    'after','before','during','about','into','out','off','so',
}

def tokenise(text: str) -> list:
    text = re.sub(r'[^a-z0-9\s]', ' ', (text or '').lower())
    return [w for w in text.split() if w not in STOPWORDS and len(w) > 2]

def tfidf_vector(tokens: list, idf: dict) -> dict:
    tf = Counter(tokens)
    total = len(tokens) or 1
    return {w: (tf[w] / total) * idf.get(w, 1.0) for w in tf}

def cosine(v1: dict, v2: dict) -> float:
    keys = set(v1) & set(v2)
    if not keys:
        return 0.0
    dot = sum(v1[k] * v2[k] for k in keys)
    mag1 = sqrt(sum(x*x for x in v1.values()))
    mag2 = sqrt(sum(x*x for x in v2.values()))
    return dot / (mag1 * mag2) if mag1 and mag2 else 0.0

def build_idf(token_lists: list) -> dict:
    N = len(token_lists)
    df = Counter()
    for tl in token_lists:
        for w in set(tl):
            df[w] += 1
    return {w: log((N + 1) / (cnt + 1)) + 1 for w, cnt in df.items()}

def source_rank(source: str) -> int:
    s = (source or '').lower()
    for i, name in enumerate(SOURCE_PRIORITY):
        if name in s:
            return i
    return 999

def run(hours: int = 48) -> int:
    print("🔁 AgentZ — Deduplicator")
    articles = get_pending_dedup(hours)

    if len(articles) < 2:
        print(f"  ℹ  Only {len(articles)} article(s) — nothing to compare.\n")
        return 0

    duplicated_ids = set()
    dup_count = 0

    # ── Pass 1: exact title dedup ─────────────────────────────────────────────
    seen_titles = {}
    for art in articles:
        title = (art.get('title') or '').strip().lower()
        if not title:
            continue
        if title in seen_titles:
            duplicated_ids.add(art['id'])
            mark_duplicate(art['id'])
            dup_count += 1
        else:
            seen_titles[title] = art['id']

    # ── Pass 2: TF-IDF cosine similarity ─────────────────────────────────────
    corpus = []
    for art in articles:
        combined = (art.get('title', '') or '') + ' ' + (art.get('summary_60w', '') or art.get('full_text', '') or '')
        corpus.append(tokenise(combined))

    idf = build_idf(corpus)
    vectors = [tfidf_vector(tl, idf) for tl in corpus]

    for i in range(len(articles)):
        if articles[i]['id'] in duplicated_ids:
            continue
        for j in range(i + 1, len(articles)):
            if articles[j]['id'] in duplicated_ids:
                continue

            sim = cosine(vectors[i], vectors[j])
            if sim >= SIMILARITY_THRESHOLD:
                rank_i = source_rank(articles[i].get('source', ''))
                rank_j = source_rank(articles[j].get('source', ''))
                victim_id = articles[j]['id'] if rank_i <= rank_j else articles[i]['id']
                duplicated_ids.add(victim_id)
                mark_duplicate(victim_id)
                dup_count += 1

    print(f"  🔍 Compared {len(articles)} articles, removed {dup_count} duplicates (threshold={SIMILARITY_THRESHOLD})\n")
    return dup_count


if __name__ == '__main__':
    run()