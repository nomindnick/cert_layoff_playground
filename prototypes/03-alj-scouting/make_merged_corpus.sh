#!/usr/bin/env bash
# Compose a multi-era corpus by symlinking two corpus roots' decision records
# into one tree (NO data copied — pure links, so privacy is preserved and the
# corpus still lives outside this repo). corpuslib runs unchanged on the result
# via CORPUS_ROOT=<merged>. Used by longitudinal.py for the cross-era P2 transfer
# test (2004/2009 spike + 2018-2025 production).
#
# Usage: make_merged_corpus.sh [SPIKE_ROOT] [NEW_ROOT] [MERGED_ROOT]
set -euo pipefail
SPIKE="${1:-/home/nick/Projects/cert_layoff_lab/output}"
NEW="${2:-/home/nick/Projects/cert_layoff_corpus/output}"
MERGED="${3:-/home/nick/Projects/cert_layoff_merged}"

rm -rf "$MERGED"
mkdir -p "$MERGED/corpus/decisions"
# decision JSONs from both eras — disjoint years, so no filename collisions
ln -s "$SPIKE"/corpus/decisions/*.json "$MERGED/corpus/decisions/"
ln -s "$NEW"/corpus/decisions/*.json   "$MERGED/corpus/decisions/"
# the richer summaries (gold / taxonomy / case_index) come from production
ln -s "$NEW/summaries" "$MERGED/summaries"

echo "merged corpus at $MERGED"
echo "  decisions:     $(ls "$MERGED/corpus/decisions" | wc -l)"
echo "  gold holdings: $(wc -l < "$MERGED/summaries/holdings.jsonl")"
echo "use it with:  export CORPUS_ROOT=$MERGED"
