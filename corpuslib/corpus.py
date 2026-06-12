"""Single data-access layer for every prototype.

Prototypes never hardcode corpus paths. The source corpus is configured here
(env var override first, then config.json, then the spike default), so when
the production corpus repo exists everything re-points with one change.
"""

import json
import os
from pathlib import Path

_DEFAULT_ROOT = "/home/nick/Projects/cert_layoff_lab/output"
_CONFIG = Path(__file__).parent / "config.json"


def corpus_paths():
    """Resolve corpus locations. Override order: $CORPUS_ROOT > config.json > spike default."""
    root = os.environ.get("CORPUS_ROOT")
    if not root and _CONFIG.exists():
        root = json.loads(_CONFIG.read_text()).get("corpus_root")
    root = Path(root or _DEFAULT_ROOT)
    return {
        "root": root,
        "decisions": root / "corpus" / "decisions",
        "gold_holdings": root / "summaries" / "holdings.jsonl",
        "taxonomy": root / "summaries" / "taxonomy.json",
        "case_index": root / "summaries" / "case_index.jsonl",
        "eval": root / "eval",
    }


def load_decisions(year=None):
    """Yield (oah_case_no, record) for every extracted decision JSON.

    PRIVACY: records contain respondent names (roster, dispositions, full_text).
    Nothing derived from them may be committed unless de-identified to
    District (ALJ) cites.
    """
    d = corpus_paths()["decisions"]
    for f in sorted(d.glob("*.json")):
        if year and not f.stem.startswith(str(year)):
            continue
        yield f.stem, json.loads(f.read_text())


def load_gold_holdings(years=None):
    """Yield gold-holding dicts from the human summary volumes (1979-2015).

    Already de-identified by the volumes' own convention (District + ALJ).
    Filter with years=an int, or an iterable of ints, matched on sort_year.
    """
    if isinstance(years, int):
        years = {years}
    elif years is not None:
        years = set(years)
    with open(corpus_paths()["gold_holdings"]) as fh:
        for line in fh:
            h = json.loads(line)
            if years is None or h.get("sort_year") in years:
                yield h


def load_taxonomy():
    return json.loads(corpus_paths()["taxonomy"].read_text())


def load_case_index():
    with open(corpus_paths()["case_index"]) as fh:
        return [json.loads(line) for line in fh]
