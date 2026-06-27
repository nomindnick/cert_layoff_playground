#!/usr/bin/env bash
# E0 prerequisite: build the 3-era merged corpus (spike 2004/2009 + production
# 1999-2001/2018-25) by symlink, reusing 03's make_merged_corpus.sh. No data is
# copied — pure links, corpus stays outside the repo. corpuslib runs unchanged
# on the result via CORPUS_ROOT.
#
# Usage: setup_merged_corpus.sh            # default merged root
#        source setup_merged_corpus.sh     # also exports CORPUS_ROOT for the shell
set -euo pipefail
MERGED="${MERGED_ROOT:-/home/nick/Projects/cert_layoff_merged}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$HERE/../03-alj-scouting/make_merged_corpus.sh" \
     /home/nick/Projects/cert_layoff_lab/output \
     /home/nick/Projects/cert_layoff_corpus/output \
     "$MERGED"
export CORPUS_ROOT="$MERGED"
echo "CORPUS_ROOT=$CORPUS_ROOT"
