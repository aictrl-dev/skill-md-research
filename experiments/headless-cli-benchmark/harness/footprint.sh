#!/usr/bin/env bash
# Install footprint per harness image: image size over its base, and installed package/binary size.
#   harness/footprint.sh > results/footprint.json
set -euo pipefail
size() { docker image inspect -f '{{.Size}}' "$1"; }
declare -A WHAT=(
  [aictrl-main]=/usr/local/bin/aictrl
  [aictrl-npm]=/usr/local/lib/node_modules/@aictrl
  [pi]=/usr/local/lib/node_modules/@mariozechner
  [pi-1.3-node22]=/usr/local/lib/node_modules/@earendil-works
  [codex]=/usr/local/lib/node_modules/@openai
  [opencode]=/usr/local/lib/node_modules/opencode-ai
)
echo "{"
first=1
for tool in aictrl-main aictrl-npm pi pi-1.3-node22 codex opencode; do
  base=bench-cmp:base; [[ $tool == *node22 ]] && base=bench-cmp:base22
  delta=$(( $(size bench-cmp:$tool) - $(size $base) ))
  installed=$(docker run --rm --entrypoint du bench-cmp:$tool -sbL "${WHAT[$tool]}" | cut -f1)
  [ $first = 1 ] || echo ","
  first=0
  printf '  "%s": {"imageDeltaMB": %s, "installedMB": %s, "path": "%s"}' "$tool" \
    "$(echo "$delta / 1048576" | bc -l)" "$(echo "$installed / 1048576" | bc -l)" "${WHAT[$tool]}"
done
echo
echo "}"
