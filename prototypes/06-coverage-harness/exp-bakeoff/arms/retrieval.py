"""Deterministic within-category retrieval for the depth arms (GPU-free).

For a spotted issue, return the top-k analogous holdings (with their de-identified
facts + ALJ reasoning), ranked by TF-IDF cosine to the matter facts, EXCLUDING the
source decision and its related proceedings (no self-retrieval). Pure Python — no
embeddings/engine dependency; upgrade to F1 embeddings later if lexical limits recall.
"""

import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.corpus import holdings        # noqa: E402
from harness.metrics import _content       # noqa: E402

_BY_CAT = None


def _index():
    global _BY_CAT
    if _BY_CAT is None:
        _BY_CAT = defaultdict(list)
        for h in holdings():
            if h["category"]:
                _BY_CAT[h["category"]].append(h)
    return _BY_CAT


def _num(case_no):
    return re.sub(r"\D", "", case_no or "")


def _vec(tokens, idf):
    tf = Counter(tokens)
    return {t: tf[t] * idf.get(t, 0.0) for t in tf}


def _cos(a, b):
    common = set(a) & set(b)
    num = sum(a[t] * b[t] for t in common)
    da = math.sqrt(sum(v * v for v in a.values()))
    db = math.sqrt(sum(v * v for v in b.values()))
    return num / (da * db) if da and db else 0.0


def retrieve(matter, category, exclude_case_nos, k=6, balanced=False):
    """Top-k analogous holdings by TF-IDF cosine to the matter.

    balanced=True: split k roughly 50/50 between district-prevailed and
    respondent-prevailed holdings (most-similar within each class, short class
    backfilled from the other). Counteracts the corpus's ~79% district-win skew,
    which otherwise biases the model toward predicting "district prevails" — and
    supplies the reasoning for HOW a district loses on a similar pattern."""
    cands = [h for h in _index().get(category, [])
             if _num(h["case_no"]) not in exclude_case_nos]
    if not cands:
        return []
    docs = [_content(" ".join([h["issue_statement"], *h["facts"], h["reasoning"]]))
            for h in cands]
    df = Counter()
    for d in docs:
        df.update(set(d))
    N = len(docs)
    idf = {t: math.log(N / df[t]) for t in df}
    mvec = _vec(_content(matter["matter_text"]), idf)
    ranked = [(s, h) for s, h in
              sorted(((_cos(mvec, _vec(d, idf)), h) for d, h in zip(docs, cands)),
                     key=lambda x: -x[0]) if s > 0]
    if not balanced:
        return [h for s, h in ranked[:k]]
    half = k // 2
    dist = [h for s, h in ranked if h["prevailing_party"] == "district"]
    resp = [h for s, h in ranked if h["prevailing_party"] == "respondent"]
    other = [h for s, h in ranked
             if h["prevailing_party"] not in ("district", "respondent")]
    pick = dist[:half] + resp[:half]
    # backfill to k from the remaining most-similar (preserving overall ranking)
    if len(pick) < k:
        chosen = set(id(h) for h in pick)
        pool = dist[half:] + resp[half:] + other
        pool.sort(key=lambda h: [s for s, hh in ranked if hh is h][0], reverse=True)
        for h in pool:
            if id(h) not in chosen:
                pick.append(h)
                if len(pick) >= k:
                    break
    return pick
