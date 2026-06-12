"""Hybrid search engine: BM25 + embedding cosine, fused with RRF (k=60).

Filters pre-restrict the candidate set (not post-filter of top-k), so
filtered queries still return k results when they exist. The `decisions`
collection is BM25-only (no embeddings over full text).
"""

import sys
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from build_index import (  # noqa: E402
    DEFAULT_MODEL, MODELS, EMBEDDED_COLLECTIONS,
    build_or_load, load_st_model, tokenize,
)

RRF_K = 60


class Engine:
    def __init__(self, model_key=DEFAULT_MODEL):
        self.model_key = model_key
        self.cfg = MODELS[model_key]
        self._indexes = {}
        self._bm25 = {}
        self._st = None

    def _index(self, collection):
        if collection not in self._indexes:
            self._indexes[collection] = build_or_load(collection, self.model_key)
        return self._indexes[collection]

    def _bm25_for(self, collection):
        if collection not in self._bm25:
            self._bm25[collection] = BM25Okapi(self._index(collection)["tokens"])
        return self._bm25[collection]

    def _encode_query(self, query):
        if self._st is None:
            self._st = load_st_model(self.model_key)
        v = self._st.encode([self.cfg["query_prefix"] + query],
                            normalize_embeddings=True)
        return np.asarray(v[0], dtype="float32")

    def _candidates(self, collection, filters):
        idx = self._index(collection)
        metas = idx["metas"]
        if not filters:
            return np.arange(len(metas))
        keep = []
        for i, m in enumerate(metas):
            if _match(m, filters):
                keep.append(i)
        return np.asarray(keep, dtype=int)

    def search(self, collection, query, filters=None, k=10, mode="hybrid"):
        """Return up to k results: {id, score, meta, text}."""
        idx = self._index(collection)
        cand = self._candidates(collection, filters)
        if len(cand) == 0:
            return []
        if collection not in EMBEDDED_COLLECTIONS and mode != "bm25":
            mode = "bm25"

        ranks = {}  # doc index -> list of ranks across signals
        if mode in ("hybrid", "bm25"):
            scores = np.asarray(self._bm25_for(collection).get_scores(tokenize(query)))
            order = cand[np.argsort(-scores[cand], kind="stable")]
            for r, di in enumerate(order):
                ranks.setdefault(int(di), []).append(r)
        if mode in ("hybrid", "embed"):
            qv = self._encode_query(query)
            sims = idx["emb"][cand] @ qv
            order = cand[np.argsort(-sims, kind="stable")]
            for r, di in enumerate(order):
                ranks.setdefault(int(di), []).append(r)

        fused = sorted(
            ((sum(1.0 / (RRF_K + r) for r in rs), di) for di, rs in ranks.items()),
            key=lambda t: -t[0],
        )
        out = []
        for score, di in fused[:k]:
            out.append({
                "id": idx["ids"][di],
                "score": round(float(score), 5),
                "meta": idx["metas"][di],
                "text": idx["texts"][di],
            })
        return out

    def rank_of(self, collection, query, target_id, filters=None, mode="hybrid"):
        """1-based rank of target_id in the full ranking (None if absent).
        Used by the known-item eval."""
        idx = self._index(collection)
        results = self.search(collection, query, filters,
                              k=len(idx["ids"]), mode=mode)
        for r, hit in enumerate(results, 1):
            if hit["id"] == target_id:
                return r
        return None

    def list_facets(self, collection):
        idx = self._index(collection)
        facets = {}
        for m in idx["metas"]:
            for key in ("year", "category", "categories", "district", "alj",
                        "prevailing_party", "overall"):
                v = m.get(key)
                if v is None:
                    continue
                vals = v if isinstance(v, list) else [v]
                slot = facets.setdefault("category" if key == "categories" else key, {})
                for x in vals:
                    slot[x] = slot.get(x, 0) + 1
        return {k: dict(sorted(v.items(), key=lambda t: -t[1])) for k, v in facets.items()}


def _match(meta, filters):
    for key, want in filters.items():
        if want in (None, ""):
            continue
        if key == "year":
            if str(meta.get("year")) != str(want):
                return False
        elif key == "category":
            cats = meta.get("categories")
            if cats is not None:
                if want not in cats:
                    return False
            elif meta.get("category") != want:
                return False
        elif key in ("district", "alj"):
            # substring, case-insensitive: district/ALJ strings are raw and
            # un-canonicalized (spelling variants exist — SPEC: note, don't solve)
            w = str(want).lower()
            own = " ".join(str(meta.get(f) or "") for f in (key, f"{key}_raw")).lower()
            cites = meta.get("cites") or []
            cite_vals = " ".join(str(c.get(key) or "") for c in cites).lower()
            if w not in own and w not in cite_vals:
                return False
        else:
            if meta.get(key) != want:
                return False
    return True
