"""Shared loading for the taste judge: candidates + labels + de-identified
holding views, derived from the lab's alignment files and decision records."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from corpuslib import corpus_paths, load_decisions, load_gold_holdings  # noqa: E402
from corpuslib.deident import deidentify  # noqa: E402

OUT = HERE / "output"
YEARS = (2009, 2004)
POSITIVE = ("matched", "category_divergent_match")
NEGATIVE = ("over_recovery",)


def _d(text, rec):
    out, _ = deidentify(text or "", rec)
    return out


def load_candidates(year):
    """One dict per extracted holding with a label from the alignment.

    label 1 = the human volume catalogued it (matched / category-divergent
    match); 0 = over_recovery (the editors omitted it). All text fields are
    de-identified here, at load time — names never enter prompts/artifacts.
    """
    align = json.loads(
        (corpus_paths()["eval"] / f"alignment_{year}.json").read_text())
    recs = {c: r for c, r in load_decisions(year=year)}
    out = []
    for s in align["system"]:
        if s["status"] in POSITIVE:
            label = 1
        elif s["status"] in NEGATIVE:
            label = 0
        else:
            continue
        rec = recs.get(s["case_no"])
        if rec is None:
            continue
        try:
            h = rec["holdings"][s["holding_idx"]]
        except IndexError:
            continue
        issue = h.get("issue") or {}
        ruling = h.get("ruling") or {}
        auths = h.get("authorities") or []
        args = h.get("arguments") or []
        text = " ".join(p for p in (
            issue.get("statement"),
            h.get("summary_style_holding"),
            (h.get("reasoning") or {}).get("summary")) if p)
        out.append({
            "id": f"{s['case_no']}:{s['holding_idx']}",
            "year": str(year),
            "label": label,
            "status": s["status"],
            "category": issue.get("category"),
            "subtype": issue.get("subtype"),
            "prevailing_party": ruling.get("prevailing_party"),
            "remedies": ruling.get("remedies") or [],
            "text": _d(text, rec),
            "summary": _d(h.get("summary_style_holding") or "", rec),
            "issue_statement": _d(issue.get("statement") or "", rec),
            "reasoning": _d((h.get("reasoning") or {}).get("summary") or "", rec),
            "authorities": [
                {"cite": a.get("raw_cite"), "type": a.get("type"),
                 "role": a.get("role")} for a in auths],
            "arguments": [
                {"party": a.get("party"), "summary": _d(a.get("summary") or "", rec)}
                for a in args],
        })
    return out


def load_prior_gold(year):
    """Gold holdings from volumes strictly before `year` (the settled-law
    context a `year` editor carried). Header rows excluded."""
    out = []
    for i, g in enumerate(load_gold_holdings()):
        if not g.get("category_raw"):
            continue
        sy = g.get("sort_year")
        if sy is None or sy >= year:
            continue
        text = (g.get("text") or "").strip()
        if text:
            out.append({"id": f"g{i}", "year": sy, "text": text,
                        "categories": g.get("category_canonical") or []})
    return out


def embed(texts, st_model=None, query=False):
    """arctic-l-v2 embeddings, normalized float32 (prototype-01 conventions:
    'query: ' prefix on queries only)."""
    import numpy as np
    from sentence_transformers import SentenceTransformer
    if st_model is None:
        st_model = SentenceTransformer("Snowflake/snowflake-arctic-embed-l-v2.0")
        st_model.max_seq_length = 1024
    if query:
        texts = ["query: " + t for t in texts]
    v = st_model.encode(texts, batch_size=16, show_progress_bar=True,
                        normalize_embeddings=True)
    return np.asarray(v, dtype="float32"), st_model
