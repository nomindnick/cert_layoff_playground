#!/usr/bin/env python3
"""Stage 1b: the bars the LLM judge must clear.

  chance     stratified-random expectation at the base rate
  rule       respondent_win OR cites_case OR sim_prior_gold < median
  logistic   sklearn LR on mechanical + similarity features
             (5-fold CV on 2009; plus train-2009 -> test-2004 transfer)

Writes output/baselines.json.
"""

import json

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

from common import OUT

FEATS = ["sim_prior_gold", "sim_same_year", "respondent_win",
         "n_authorities", "cites_case", "has_arguments", "n_args", "len_text"]


def load(year):
    cands = json.loads((OUT / f"features_{year}.json").read_text())
    cats = sorted({c["category"] or "?" for c in cands})
    X, y = [], []
    for c in cands:
        f = c["features"]
        row = [f[k] for k in FEATS]
        row += [int((c["category"] or "?") == cat) for cat in cats]
        X.append(row)
        y.append(c["label"])
    return np.asarray(X, float), np.asarray(y), cats


def prf(y, pred):
    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3)}


def main():
    out = {}
    X9, y9, cats9 = load(2009)
    base = y9.mean()
    # chance: predicting include at the base rate -> P=base, R=base
    f1_chance = 2 * base * base / (2 * base) if base else 0
    out["chance_2009"] = {"precision": round(float(base), 3),
                          "recall": round(float(base), 3),
                          "f1": round(float(f1_chance), 3)}

    cands9 = json.loads((OUT / "features_2009.json").read_text())
    med = float(np.median([c["features"]["sim_prior_gold"] for c in cands9]))
    rule = np.asarray([
        1 if (c["features"]["respondent_win"] or c["features"]["cites_case"]
              or c["features"]["sim_prior_gold"] < med) else 0
        for c in cands9])
    out["rule_2009"] = prf(y9, rule)

    # logistic, 5-fold CV on 2009
    skf = StratifiedKFold(5, shuffle=True, random_state=7)
    preds = np.zeros_like(y9)
    for tr, te in skf.split(X9, y9):
        sc = StandardScaler().fit(X9[tr])
        lr = LogisticRegression(max_iter=2000, class_weight="balanced")
        lr.fit(sc.transform(X9[tr]), y9[tr])
        preds[te] = lr.predict(sc.transform(X9[te]))
    out["logistic_cv_2009"] = prf(y9, preds)

    # transfer: train 2009, test 2004 (category one-hots must align: refit on
    # shared numeric features only — categories differ between volumes)
    X9n = X9[:, :len(FEATS)]
    X4, y4, _ = load(2004)
    X4n = X4[:, :len(FEATS)]
    sc = StandardScaler().fit(X9n)
    lr = LogisticRegression(max_iter=2000, class_weight="balanced")
    lr.fit(sc.transform(X9n), y9)
    out["logistic_2009train_2004test"] = prf(y4, lr.predict(sc.transform(X4n)))
    out["coef_numeric"] = dict(zip(FEATS, [round(float(c), 3) for c in lr.coef_[0]]))

    (OUT / "baselines.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
