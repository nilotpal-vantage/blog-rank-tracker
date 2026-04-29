#!/bin/bash
# refresh.sh — refresh GSC data and push to GitHub.
# Designed to run unattended via cron. Idempotent — no-ops cleanly if nothing changed.
# Logs to ~/.blog-rank-tracker.log

set -e

cd /Users/nilotpalsaharia/KWID/projects/blog-rank-tracker

# Cron has a minimal PATH; cover Homebrew + system locations.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

echo "==================== $(date) ===================="

# Pull the tracker repo first while the working tree is clean, so the rebase
# can't trip on the about-to-be-regenerated data files.
git pull --rebase --quiet

# Best-effort pull of the Astro repo so new co-authored posts get picked up.
# Non-fatal if it fails (you pull daily anyway).
git -C ../../vantagecircle-astro pull --ff-only --quiet \
  || echo "[warn] Astro pull failed; proceeding with local clone state."

# Regenerate data.js + rankings.js
python3 update-data.py

# Push only if data files actually changed
if ! git diff --quiet data.js rankings.js; then
  git add data.js rankings.js
  git commit -m "Auto-refresh data ($(date '+%Y-%m-%d'))"
  git push --quiet
  echo "[ok] Pushed refresh."
else
  echo "[ok] No changes — nothing to push."
fi
