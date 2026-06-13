#!/usr/bin/env python3
"""Build-or-load search indexes for the three collections.

Collections:
  holdings       extracted holdings (2004/2009 decision records), BM25 + embeddings
  gold_holdings  human-volume holdings 1979-2015, BM25 + embeddings
  decisions      full decision texts, BM25 only

Each index pickles to output/indexes/{collection}__{model}.pkl keyed by a
content hash of (doc ids, doc texts, model id); rebuilds only when the corpus
or model changes. Embeddings are L2-normalized float32 (cosine = dot).

Usage: build_index.py [--model arctic-l-v2|bge-large] [--force]
"""

import argparse
import hashlib
import json
import pickle
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # repo root, for corpuslib

from corpuslib import load_decisions, load_gold_holdings  # noqa: E402
from corpuslib.deident import alj_surname, deidentify, district_short  # noqa: E402

OUT = HERE / "output" / "indexes"

# Open models benchmarked in fppc-tuned-embeddings (results/check2_*).
# arctic-l-v2 won there (MRR 0.522, above the OpenAI baseline); bge-large
# was second. Prefixes per each model's card — queries only, no doc prefix.
MODELS = {
    "arctic-l-v2": {
        "hf_id": "Snowflake/snowflake-arctic-embed-l-v2.0",
        "query_prefix": "query: ",
        "doc_prefix": "",
        "max_seq": 1024,
    },
    "bge-large": {
        "hf_id": "BAAI/bge-large-en-v1.5",
        "query_prefix": "Represent this sentence for searching relevant passages: ",
        "doc_prefix": "",
        "max_seq": 512,
    },
}
DEFAULT_MODEL = "arctic-l-v2"

EMBEDDED_COLLECTIONS = ("holdings", "gold_holdings")


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def holding_text(h):
    """The searchable composition for one extracted holding. Single function
    so the composition is easy to revisit (SPEC experiment)."""
    parts = [
        (h.get("issue") or {}).get("statement"),
        h.get("summary_style_holding"),
        (h.get("reasoning") or {}).get("summary"),
    ]
    return " ".join(p.strip() for p in parts if p)


def build_holdings_docs():
    ids, texts, metas = [], [], []
    for case_no, rec in load_decisions():
        ident = rec.get("identity") or {}
        district_raw = (ident.get("district") or {}).get("raw") or ""
        alj_raw = (ident.get("alj") or {}).get("raw") or ""
        outcome = rec.get("outcome") or {}
        for i, h in enumerate(rec.get("holdings") or []):
            text = holding_text(h)
            if not text:
                continue
            # privacy by construction: respondent names never enter the index,
            # so search results and snippets are District (ALJ)-safe everywhere
            text, _ = deidentify(text, rec)
            summary, _ = deidentify(h.get("summary_style_holding") or "", rec)
            ids.append(f"{case_no}:{i}")
            texts.append(text)
            metas.append({
                "case_no": case_no,
                "holding_idx": i,
                "year": case_no[:4],
                "category": (h.get("issue") or {}).get("category"),
                "subtype": (h.get("issue") or {}).get("subtype"),
                "district_raw": district_raw,
                "district": district_short(district_raw),
                "alj_raw": alj_raw,
                "alj": alj_surname(alj_raw),
                "prevailing_party": (h.get("ruling") or {}).get("prevailing_party"),
                "remedies": (h.get("ruling") or {}).get("remedies") or [],
                "overall": outcome.get("overall"),
                "decision_kind": ident.get("decision_kind"),
                "summary": summary,
            })
    return ids, texts, metas


def build_gold_docs():
    ids, texts, metas = [], [], []
    for i, h in enumerate(load_gold_holdings()):
        # rows with no category_raw are volume headers/front-matter, not holdings
        if not h.get("category_raw"):
            continue
        text = (h.get("text") or "").strip()
        if not text:
            continue
        ids.append(f"g{i}")
        texts.append(text)
        metas.append({
            "year": str(h.get("sort_year") or ""),
            "categories": h.get("category_canonical") or [],
            "letter_title": h.get("letter_title"),
            "cites": h.get("cites") or [],
            "volume": h.get("volume"),
            "summary": text,
        })
    return ids, texts, metas


def build_decision_docs():
    ids, texts, metas = [], [], []
    for case_no, rec in load_decisions():
        ident = rec.get("identity") or {}
        district_raw = (ident.get("district") or {}).get("raw") or ""
        alj_raw = (ident.get("alj") or {}).get("raw") or ""
        ids.append(case_no)
        texts.append(rec.get("full_text") or "")
        metas.append({
            "case_no": case_no,
            "year": case_no[:4],
            "district_raw": district_raw,
            "district": district_short(district_raw),
            "alj_raw": alj_raw,
            "alj": alj_surname(alj_raw),
            "overall": (rec.get("outcome") or {}).get("overall"),
            "decision_kind": ident.get("decision_kind"),
            "n_holdings": len(rec.get("holdings") or []),
        })
    return ids, texts, metas


BUILDERS = {
    "holdings": build_holdings_docs,
    "gold_holdings": build_gold_docs,
    "decisions": build_decision_docs,
}


def content_hash(ids, texts, model_id):
    h = hashlib.sha1()
    h.update(json.dumps([ids, texts], sort_keys=True).encode())
    h.update(model_id.encode())
    return h.hexdigest()


def index_path(collection, model_key):
    suffix = model_key if collection in EMBEDDED_COLLECTIONS else "bm25"
    return OUT / f"{collection}__{suffix}.pkl"


def build_or_load(collection, model_key=DEFAULT_MODEL, force=False, st_model=None):
    """Return the index dict for a collection, building it if stale/missing."""
    cfg = MODELS[model_key]
    ids, texts, metas = BUILDERS[collection]()
    model_id = cfg["hf_id"] if collection in EMBEDDED_COLLECTIONS else "none"
    chash = content_hash(ids, texts, model_id)
    path = index_path(collection, model_key)
    if path.exists() and not force:
        with open(path, "rb") as f:
            idx = pickle.load(f)
        if idx.get("hash") == chash:
            return idx
        print(f"[{collection}] stale index (corpus/model changed) — rebuilding")
    idx = {
        "hash": chash,
        "collection": collection,
        "model_key": model_key,
        "model_id": model_id,
        "ids": ids,
        "texts": texts,
        "metas": metas,
        "tokens": [tokenize(t) for t in texts],
        "emb": None,
    }
    if collection in EMBEDDED_COLLECTIONS:
        import numpy as np
        if st_model is None:
            st_model = load_st_model(model_key)
        print(f"[{collection}] embedding {len(texts)} docs with {cfg['hf_id']} ...")
        emb = st_model.encode(
            [cfg["doc_prefix"] + t for t in texts],
            batch_size=16, show_progress_bar=True, normalize_embeddings=True,
        )
        idx["emb"] = np.asarray(emb, dtype="float32")
    OUT.mkdir(parents=True, exist_ok=True)
    # atomic write: a concurrent reader never sees a half-written pickle
    tmp = path.with_suffix(".pkl.tmp")
    with open(tmp, "wb") as f:
        pickle.dump(idx, f)
    tmp.replace(path)
    print(f"[{collection}] built: {len(ids)} docs -> {path.name}")
    return idx


def load_st_model(model_key=DEFAULT_MODEL):
    from sentence_transformers import SentenceTransformer
    cfg = MODELS[model_key]
    m = SentenceTransformer(cfg["hf_id"])
    m.max_seq_length = cfg["max_seq"]
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL, choices=list(MODELS))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    st = load_st_model(args.model)
    for c in BUILDERS:
        build_or_load(c, args.model, force=args.force, st_model=st)


if __name__ == "__main__":
    main()
