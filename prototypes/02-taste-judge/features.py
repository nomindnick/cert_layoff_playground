#!/usr/bin/env python3
"""Stage 1: deterministic features per candidate, cached to
output/features_{year}.json (+ neighbor lists for the judge's context arms
and embeddings for assemble.py).

Features:
  sim_prior_gold   max cosine vs all prior-year gold holdings ("settledness")
  sim_same_year    max cosine vs other same-year candidates (duplication)
  respondent_win   prevailing_party in (respondent, mixed)
  n_authorities, cites_case, has_arguments, n_args, len_text
Neighbors (top-5 each) are stored with similarity + truncated text so
judge.py never needs the embedding model.
"""

import json

import numpy as np

from common import OUT, YEARS, embed, load_candidates, load_prior_gold

TOP_K = 5


def main():
    OUT.mkdir(exist_ok=True)
    st = None
    for year in YEARS:
        cands = load_candidates(year)
        prior = load_prior_gold(year)
        print(f"[{year}] {len(cands)} candidates "
              f"({sum(c['label'] for c in cands)} positive), "
              f"{len(prior)} prior-gold holdings")
        c_emb, st = embed([c["text"] for c in cands], st)
        g_emb, st = embed([g["text"] for g in prior], st)

        sims_prior = c_emb @ g_emb.T                      # (n_c, n_g)
        sims_self = c_emb @ c_emb.T
        np.fill_diagonal(sims_self, -1.0)

        for i, c in enumerate(cands):
            order_g = np.argsort(-sims_prior[i])[:TOP_K]
            order_c = np.argsort(-sims_self[i])[:TOP_K]
            c["features"] = {
                "sim_prior_gold": round(float(sims_prior[i].max()), 4),
                "sim_same_year": round(float(sims_self[i].max()), 4),
                "respondent_win": int(c["prevailing_party"] in ("respondent", "mixed")),
                "n_authorities": len(c["authorities"]),
                "cites_case": int(any(a.get("type") == "case" for a in c["authorities"])),
                "has_arguments": int(bool(c["arguments"])),
                "n_args": len(c["arguments"]),
                "len_text": len(c["text"]),
            }
            c["prior_neighbors"] = [
                {"year": prior[j]["year"], "sim": round(float(sims_prior[i][j]), 3),
                 "text": prior[j]["text"][:240]} for j in order_g]
            c["same_year_neighbors"] = [
                {"id": cands[j]["id"], "sim": round(float(sims_self[i][j]), 3),
                 "label": cands[j]["label"],  # eval-only; judge prompts must NOT see labels
                 "text": cands[j]["text"][:240]} for j in order_c]

        (OUT / f"features_{year}.json").write_text(
            json.dumps(cands, indent=1))
        np.save(OUT / f"emb_{year}.npy", c_emb)
        print(f"[{year}] wrote features_{year}.json + emb_{year}.npy")


if __name__ == "__main__":
    main()
