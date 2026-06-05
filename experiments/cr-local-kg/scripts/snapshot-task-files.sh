#!/usr/bin/env bash
set -euo pipefail
# Snapshot the 20 tasks' source files from the pinned aictrl commit into a stable
# local dir (task-files/), so the sweep does not depend on a git worktree that
# can be pruned mid-run. Reads `repo` source from $AICTRL_SRC (default
# ../aictrl_main) at tasks.json `pinCommit`. Regenerable + reproducible.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXP_DIR="$(dirname "$SCRIPT_DIR")"
SRC="${AICTRL_SRC:-/home/bulat/code/aictrl_main}"
DEST="$EXP_DIR/task-files"
PIN="$(npx tsx -e 'console.log(JSON.parse(require("fs").readFileSync(process.argv[1])).pinCommit)' "$EXP_DIR/tasks/tasks.json")"

echo "snapshotting task files @ $PIN from $SRC -> $DEST"
rm -rf "$DEST"; mkdir -p "$DEST"
npx tsx -e '
  const t=JSON.parse(require("fs").readFileSync(process.argv[1]));
  const set=new Set(); for(const x of t.tasks) for(const p of x.paths) set.add(p);
  for(const p of set) console.log(p);
' "$EXP_DIR/tasks/tasks.json" | while read -r p; do
  mkdir -p "$DEST/$(dirname "$p")"
  git -C "$SRC" show "$PIN:$p" > "$DEST/$p"
done
echo "snapshotted $(find "$DEST" -type f | wc -l) files"