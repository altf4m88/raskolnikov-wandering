#!/usr/bin/env bash
# Rebuild index.html from scratch.
#   tools/build.sh            full pipeline (downloads OSM + Gutenberg into ./cache on first run)
#   tools/build.sh --bundle   only re-pack src/app.html with the committed data/*.json
set -euo pipefail
cd "$(dirname "$0")/.."
CACHE=cache

if [[ "${1:-}" != "--bundle" ]]; then
  python3 -I tools/fetch_osm.py "$CACHE"
  python3 -I tools/text.py "$CACHE"
  python3 -I tools/build_map.py "$CACHE" data/map.json            # also writes $CACHE/build/graph.pkl
  python3 -I tools/build_story.py data/story.json "$CACHE/chapters.json" "$CACHE/build/graph.pkl" data/map.json data/story.built.json
fi
python3 -I tools/bundle.py data/map.json data/story.built.json src/app.html "$CACHE/out"
cp "$CACHE/out/index.html" index.html
echo "index.html rebuilt ($(du -h index.html | cut -f1))"
