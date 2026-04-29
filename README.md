# Blog Rank Tracker

A static dashboard that tracks SERP positions of 73 Vantage Circle blog posts authored by Nilotpal, using Google Search Console data.

## Tabs

- **Overview** — KPI cards, top gainers and droppers (28d).
- **Rank Tracker** — full table of all posts. Default filter: page 2 + page 3+. Click any row for the 12-week history modal.
- **Movers** — "Fell off Page 1" priority queue, plus rising and bleeding sub-tables.
- **CTR Fixes** — page 1 posts with CTR < 1% and ≥1k impressions. Title/meta rewrite candidates.

## Refresh

```bash
python3 update-data.py
```

This reads frontmatter from `../../vantagecircle-astro/content/en/posts/` (filtered by author `nilotpal`), pulls fresh GSC data via OAuth tokens from `../../gsc-mcp/gsc_tokens.db`, and regenerates `data.js` + `rankings.js`. Reload the page in the browser after running.

## Files

- `index.html` — single-page dashboard. Open with `file://` or any static host.
- `data.js` — generation metadata only (period, post count, timestamp).
- `rankings.js` — full per-post records with current/prev position, delta, impressions, clicks, CTR, bucket, weekly history.
- `update-data.py` — refresh script.
- `_posts.json` — gitignored intermediate.

## Buckets

- `page1` — avg position ≤ 10
- `page2` — avg position 10.01 – 20
- `page3+` — avg position > 20
- `no-data` — no GSC impressions in the current 28-day window
