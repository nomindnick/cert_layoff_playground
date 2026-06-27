"""Grounding instrument: does a free-prose analysis CITE real corpus holdings?

The W11 thesis is that retrieval makes a local model GROUND its analysis in real
decisions instead of confabulating. The depth recovery metric is blind to this
(it scores reasoning overlap, not whether the cited cases exist). This module
scores it directly.

Models cite holdings in prose as "*District (ALJ), Year*" (the format the
evidence block feeds them: '- District (ALJ), year [hid]'). Two wrinkles drive
the design:

  1. scrub_external (applied before the analysis is saved) over-scrubs some
     DISTRICT names to "[name]" but leaves the ALJ surname + year intact. So the
     robust resolution key is (alj_surname, year), with district as a bonus
     disambiguator when it survived.
  2. closed-book analyses cite ~no corpus holdings at all (the model has no
     knowledge of these obscure OAH cases) — so the discriminating signal is
     "RAG cites resolvable, in-evidence holdings; closed-book cites ~none."

Resolution is against the live corpus (any real holding) AND, for RAG, against
the deterministically-reconstructed retrieved evidence set (was the cite one the
model was actually handed, vs a real holding it pulled from elsewhere / invented).
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO = HERE.parent
sys.path.insert(0, str(PROTO))
sys.path.insert(0, str(PROTO / "scoreboard"))

from harness.corpus import holdings              # noqa: E402

# ---- corpus cite index (built once) -----------------------------------------
_IDX = None


def _norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def _index():
    """Resolution indices keyed off fields that SURVIVE de-identification."""
    global _IDX
    if _IDX is None:
        by_alj_year = {}        # (alj, year) -> {hid}
        by_da_year = {}         # (district_token0, alj, year) -> {hid}
        by_dist_year = {}       # (district_token0, year) -> {hid}  (alj-less fallback)
        aljs = set()
        for h in holdings():
            yr, alj = h["year"], _norm(h["alj"])
            dtok = _norm((h["district"] or "").split()[0]) if h.get("district") else ""
            if alj and yr:
                by_alj_year.setdefault((alj, yr), set()).add(h["hid"])
                aljs.add(alj)
                if dtok:
                    by_da_year.setdefault((dtok, alj, yr), set()).add(h["hid"])
            if dtok and yr:
                by_dist_year.setdefault((dtok, yr), set()).add(h["hid"])
        _IDX = {"alj_year": by_alj_year, "da_year": by_da_year,
                "dist_year": by_dist_year, "aljs": aljs}
    return _IDX


# ---- cite parsing -----------------------------------------------------------
# "District (ALJ), 2009" / "*Reef-sunset Unified (Walker), 2009*" / "(Cohn), 2004"
# Require a 4-digit year right after the parenthetical surname so we don't match
# generic parentheticals like "(Permanent vs. Probationary)".
_CITE = re.compile(
    r"([A-Z][\w.,'&/ -]{0,60}?)?\(\s*(?:ALJ\s+)?([A-Z][a-zà-ÿ'’-]+)\s*\)\s*,?\s*"
    r"((?:19|20)\d{2})")


def parse_cites(text):
    """Yield (district_text_or_None, alj, year) cite tuples from prose."""
    out = []
    for m in _CITE.finditer(text or ""):
        dist, alj, yr = m.group(1), m.group(2), int(m.group(3))
        dist = dist.strip(" *,.-") if dist else None
        out.append((dist or None, alj, yr))
    return out


def resolve(cite):
    """Return the set of corpus hids a parsed cite resolves to (empty = unresolved)."""
    idx = _index()
    dist, alj, yr = cite
    alj_n = _norm(alj)
    dtok = _norm(dist.split()[0]) if dist and dist.split() else ""
    # strongest: district token + alj + year
    if dtok and (dtok, alj_n, yr) in idx["da_year"]:
        return idx["da_year"][(dtok, alj_n, yr)]
    # alj + year (survives de-id of the district)
    if (alj_n, yr) in idx["alj_year"]:
        return idx["alj_year"][(alj_n, yr)]
    # alj-less fallback (rare: model gave district + year, no/garbled alj)
    if dtok and (dtok, yr) in idx["dist_year"]:
        return idx["dist_year"][(dtok, yr)]
    return set()


# ---- per-analysis scoring ---------------------------------------------------

def score_analysis(analysis, evidence_hids=None):
    """Grounding for one analysis. evidence_hids = the reconstructed retrieved set
    (None for closed-book). Counts UNIQUE cites (a holding cited twice = once)."""
    cites = parse_cites(analysis)
    seen, uniq = set(), []
    for c in cites:
        key = (_norm(c[1]), c[2])           # (alj, year) dedup key
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    n = len(uniq)
    resolved, in_ev, unresolved = 0, 0, []
    ev = set(evidence_hids or [])
    for c in uniq:
        hids = resolve(c)
        if hids:
            resolved += 1
            if ev and (hids & ev):
                in_ev += 1
        else:
            unresolved.append(f"{c[0] or '?'} ({c[1]}), {c[2]}")
    return {
        "n_cites": n,
        "n_resolved": resolved,
        "resolution_rate": round(resolved / n, 3) if n else None,
        "n_in_evidence": in_ev if ev else None,
        "in_evidence_rate": (round(in_ev / n, 3) if (n and ev) else None),
        "unresolved": unresolved[:8],
    }
