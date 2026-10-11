#!/usr/bin/env bash
# Reconstruit tout le pack "Home Builder Kit" : assets, exports, vitrine, aperçus, archive.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python}
TMP=$(mktemp -d)
$PY tools/make_home_kit.py
mkdir -p HomeKit/Previews/Categories "$TMP/thumbs"
$PY tools/make_home_showcase.py HomeKit/Previews
for i in 0 1 2 3; do $PY tools/render_home_kit.py HomeKit/HomeBuilderKit_Library.blend "$TMP/thumbs" $i 4 400 >/dev/null 2>&1 & done; wait
$PY tools/make_sheets.py "$TMP/thumbs" HomeKit/Previews/Categories 5
