#!/bin/bash
# refresh.sh — refresh GSC data and push to GitHub.
# Designed to run unattended via launchd. Idempotent — no-ops cleanly if nothing changed.
# Logs to ~/.blog-rank-tracker.log
#
# Always refresh through this script, never `python3 update-data.py` on its own —
# a bare run regenerates the data files without committing them, and the leftovers
# block next week's rebase.

set -eEuo pipefail

cd /Users/nilotpalsaharia/KWID/projects/blog-rank-tracker

# Cron/launchd has a minimal PATH; cover Homebrew + system locations.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

echo "==================== $(date) ===================="

# An unattended failure is invisible unless it says so out loud: this script spent
# ten Mondays dying on its first git command with nobody reading the log.
notify() {
  osascript -e "display notification \"$1\" with title \"Blog Rank Tracker\" sound name \"Basso\"" >/dev/null 2>&1 || true
}
fail() {
  echo "[FAIL] $1"
  notify "$1"
  exit 1
}
trap 'fail "Aborted at line $LINENO — see ~/.blog-rank-tracker.log"' ERR

# data.js/rankings.js/queries.js are regenerated from scratch below, so a leftover
# local edit is throwaway — drop it rather than let it block the rebase.
# index.html is hand-maintained, so --autostash carries real edits across instead.
git checkout -- data.js rankings.js queries.js 2>/dev/null || true
git pull --rebase --autostash --quiet

# Best-effort pull of the Astro repo so new co-authored posts get picked up.
# Non-fatal if it fails (you pull daily anyway).
git -C ../../vantagecircle-astro pull --ff-only --quiet \
  || echo "[warn] Astro pull failed; proceeding with local clone state."

# Regenerate data.js + rankings.js + queries.js, and the index.html cache-bust.
python3 update-data.py

# Refuse to publish obvious junk over good data — an expired token or an empty GSC
# response should not overwrite a working dashboard.
python3 - <<'PY' || fail "Sanity check failed — not publishing"
import datetime, json, sys
raw = open("data.js").read()
meta = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
age = (datetime.date.today() - datetime.date.fromisoformat(meta["history_end"])).days
if age > 14:
    sys.exit(f"newest data is {age} days old ({meta['history_end']})")
if meta["post_count"] < 20:
    sys.exit(f"only {meta['post_count']} posts matched")
print(f"[ok] sanity: {meta['post_count']} posts, data through {meta['last_week']}")
PY

# Push only if data files (or the index.html cache-bust pointer) actually changed
if ! git diff --quiet data.js rankings.js queries.js index.html; then
  git add data.js rankings.js queries.js index.html
  git commit -m "Auto-refresh data ($(date '+%Y-%m-%d'))" --quiet
  git push --quiet
  echo "[ok] Pushed refresh."
else
  echo "[ok] No changes — nothing to push."
fi

# Anything still uncommitted here is what breaks *next* week's rebase. Say so now.
if ! git diff --quiet; then
  echo "[warn] working tree still dirty after commit:"
  git status --short
  notify "Refresh pushed, but left uncommitted changes — next run may fail"
fi
