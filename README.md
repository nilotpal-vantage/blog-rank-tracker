# Blog Rank Tracker

A static dashboard that tracks SERP positions of 73 Vantage Circle blog posts authored by Nilotpal, using Google Search Console data.

## Features

- **52 weeks of weekly history** per slug (position, impressions, clicks, CTR)
- **Window selector**: 4 / 12 / 26 / 52 weeks, or custom ISO-week range
- **CSV export**: summary (current view) + weekly long-format (all history)
- **Click any blog**: modal with full weekly trend chart (metric picker) + history table
- **Tabs**: Overview / Rank Tracker / Movers / CTR Fixes

## Refresh

### Manual

```bash
cd ~/KWID/projects/blog-rank-tracker
./refresh.sh
```

`refresh.sh` runs `update-data.py`, commits, and pushes if anything changed. The Python script reads frontmatter from `../../vantagecircle-astro/content/en/posts/` (filtered by author = `nilotpal`), pulls 52 weeks of weekly GSC data via the OAuth tokens in `../../gsc-mcp/gsc_tokens.db`, and regenerates `data.js` + `rankings.js`. Runs in ~10 seconds.

After push, GitHub Pages rebuilds in ~30 seconds. Hard-refresh the dashboard (Cmd+Shift+R) to bypass JS caching.

### Automated (Mondays at 10:00 IST)

Installed as a macOS launchd agent at `~/Library/LaunchAgents/com.nilotpal.blog-rank-tracker.plist`. Logs to `~/.blog-rank-tracker.log`.

```bash
# disable
launchctl unload ~/Library/LaunchAgents/com.nilotpal.blog-rank-tracker.plist

# re-enable
launchctl load ~/Library/LaunchAgents/com.nilotpal.blog-rank-tracker.plist

# check status
launchctl list | grep nilotpal

# tail logs
tail -f ~/.blog-rank-tracker.log
```

Runs only when the Mac is awake. If your Mac is asleep at the trigger time, launchd waits until next wake — no missed Mondays as long as you open the laptop the same day.

## Files

- `index.html` — single-page dashboard. All comparisons (current vs prior window) computed in JS from the weekly history.
- `data.js` — meta only: `{history_start, history_end, all_weeks, generated_at, post_count}`.
- `rankings.js` — per-post metadata + `history[]` array of `{w, p, i, c, ctr}`.
- `update-data.py` — refresh script.
- `_posts.json` — gitignored intermediate.

## Buckets

- `page1` — avg position ≤ 10 over the selected window
- `page2` — avg position 10.01 – 20
- `page3+` — avg position > 20
- `no-data` — no GSC impressions in the selected window
