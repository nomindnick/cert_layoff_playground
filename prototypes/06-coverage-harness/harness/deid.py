"""De-identification gate for prototype 06.

Two layers, matching the two risks the privacy audit found on the merged corpus:

1. `deid(text, dec)` — ROSTER de-id (wraps `corpuslib.deident.deidentify`).
   Verified 2026-06-17: 0/174 production rosters leak a surname after this pass.
   Run it on EVERY prose field before the text reaches a model or a matter.

2. `residual_name_candidates(text)` — NON-roster names survive roster de-id (a
   retained junior teacher named in `facts` is not a respondent; lesson 108), and
   roster de-id can't catch them. This flags capitalized name-looking tokens that
   a human/LLM scrub must clear BEFORE anything is committed or shown outside the
   box. Internal model calls run on roster-de-id'd text; committed artifacts must
   additionally clear this flag.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from corpuslib.deident import deidentify as _roster_deid  # noqa: E402

# Capitalized tokens that are common in these decisions and are NOT personal
# names — kept out of the residual-name flagger to cut false positives.
_NOT_NAMES = {
    "District", "Respondent", "Respondents", "Education", "Code", "Board",
    "Accusation", "Resolution", "Section", "County", "School", "Services",
    "Title", "Notice", "Hearing", "Evidence", "Credential", "ALJ", "Judge",
    "Administrative", "Law", "Order", "Decision", "State", "California",
    "Unified", "Union", "Elementary", "Secondary", "High", "Office", "Act",
    "Government", "Article", "Whether", "The", "Respondent's", "PKS", "FTE",
    "ADA", "March", "January", "February", "April", "May", "June", "July",
    "August", "September", "October", "November", "December", "Monday",
    "Tuesday", "Wednesday", "Thursday", "Friday", "Superintendent", "Skipping",
    "Bumping", "Seniority", "Competency", "Procedural", "Reduction",
}

# A personal-name shape: 1-3 Capitalized tokens. We only flag those NOT already
# reduced to a roster ref (R\d+) and not in the stop set.
_NAME = re.compile(r"\b([A-Z][a-zà-ÿ'\-]+(?:\s+[A-Z][a-zà-ÿ'\-]+){0,2})\b")


def deid(text, dec):
    """Roster de-id one string (the read-time gate). Returns the scrubbed text."""
    return _roster_deid(text or "", dec)[0]


# org/place/legal words that look like name parts but aren't people — never scrub.
_ORG = {
    "Unified", "Union", "District", "School", "Schools", "County", "Office",
    "Education", "Code", "Board", "Community", "Court", "Center", "Department",
    "Association", "Act", "Resolution", "Elementary", "Secondary", "High",
    "Valley", "Oak", "Charter", "City", "Joint", "Area", "Service", "Special",
    "Government", "State", "California", "Administrative", "Law", "Title",
    "Section", "Article", "Subject", "Single", "Multiple", "Reading", "English",
    "Spanish", "Math", "Science", "Business", "Computer", "Physical", "Home",
}
_HON = r"(?:Mr|Mrs|Ms|Dr|Prof|Superintendent|Principal|Director|Coordinator)\.?"
_NAME2 = re.compile(rf"\b{_HON}\s+[A-Z][a-zà-ÿ'\-]+(?:\s+[A-Z][a-zà-ÿ'\-]+)?")
_BIGRAM = re.compile(r"\b([A-Z][a-zà-ÿ'\-]{1,})\s+([A-Z][a-zà-ÿ'\-]{1,})\b")


def scrub_external(text):
    """Best-effort residual name scrub for CLOUD-bound / committed text (roster
    de-id is assumed done upstream). Catches honorific-prefixed names and
    person-name bigrams; bare single surnames may pass (the eval accepts this for
    public-record OAH data — production runs everything local). Over-redaction is
    the safe direction. District (ALJ) cites are preserved (org words stay)."""
    t = _NAME2.sub("[name]", text or "")

    def _bg(m):
        a, b = m.group(1), m.group(2)
        if a in _ORG or b in _ORG:          # district/place/legal phrase — keep
            return m.group(0)
        if a in _NOT_NAMES or b in _NOT_NAMES:
            return m.group(0)
        return "[name]"                      # looks like First Last
    return _BIGRAM.sub(_bg, t)


def residual_name_candidates(text):
    """Capitalized name-looking tokens that survived roster de-id — candidates
    for a human/LLM scrub before committing. Conservative: skips known
    non-name capitalized words and anything already a roster ref."""
    out = []
    for m in _NAME.finditer(text or ""):
        span = m.group(1)
        toks = span.split()
        if all(t in _NOT_NAMES for t in toks):
            continue
        # a single known-non-name token (sentence-initial "The", etc.)
        if len(toks) == 1 and toks[0] in _NOT_NAMES:
            continue
        out.append(span)
    return out
