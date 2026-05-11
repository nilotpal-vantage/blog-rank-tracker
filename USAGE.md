# Blog Rank Tracker — Usage Guide

Personal cheatsheet for reading and acting on the dashboard at https://nilotpal-vantage.github.io/blog-rank-tracker/.

---

## The window selector is the first decision

Every number on the dashboard is computed over the **selected window** and compared against the **prior window of the same length** (the "Δ" / delta columns).

| Window | When to use it | Why |
|---|---|---|
| **4 weeks** | Default for day-to-day work. "What is happening right now?" | Fresh enough to catch this month's algorithm/intent shifts. Noisy on low-volume posts. |
| **12 weeks** | Quarterly review. "What's the stable trend?" | Smooths out single-week wobble. Matches GSC's "Last 3 months" default. |
| **26 / 52 weeks** | "Has this post grown over the year?" | Useful for proving content investment paid off. Slow to reflect recent edits. |
| **Custom** | Pre/post specific events (algorithm update, big edit). | Pick start/end weeks bracketing the event. |

**Key mental model:** if the prior window is empty/short (e.g. you pick 26 weeks but only have 30 weeks of data), the Δ columns will be unreliable or missing. The header's "vs prior" line tells you the comparison range — always check it before believing a Δ.

---

## Tab-by-tab guide

### Overview — open first, every time

The header KPIs answer four questions in 5 seconds:

1. **Total Impressions / Clicks / Avg Position** with %-change vs prior window
   → "Is the portfolio growing or shrinking?"
   - Impressions up but clicks flat → CTR problem somewhere. Check **CTR Fixes**.
   - Position improved (Δ negative, green arrow) but impressions flat → query intent shift, your ranks are better but searches dropped.
   - Position worse + clicks down → something real happened. Go to **Movers**.

2. **Total / Page 1 / Page 2 / Page 3+** post counts
   → Distribution snapshot. Watch the Page 1 number over time — that's the real scoreboard.

3. **Gainers / Droppers / Fell off P1**
   → Quick triage counts.
   - "Fell off P1" > 0 is always urgent. Go to **Movers** and look at the "Fell off Page 1" section.

4. **Top Gainers / Top Droppers** lists
   → Click into any row for the detail modal.

**Action threshold:** if Total Impressions Δ is more than ±15%, something noteworthy happened — investigate before moving on.

---

### Rank Tracker — the main table

Lists every tracked post, one row per post.

**Columns:**
- **Pos** = impression-weighted average position over the selected window (lower = better).
- **Δ** = Pos minus Prev Pos. Negative (green ▲) = rank improved; positive (red ▼) = rank worsened.
- **Prev** = Pos over the prior window of the same length.
- **Impr / Clicks / CTR** = totals/averages for the selected window.
- **Bucket** = Page 1 (≤10), Page 2 (11–20), Page 3+ (>20), No data.
- **Trend** = sparkline of weekly position over the selected window, with `first → last` values below it. The sparkline auto-scales per row, so always trust the numbers under it, not the visual slope alone.

**Default filters:** Page 2 + Page 3+ are pre-selected (these are your optimization targets). Click Page 1 to see what's holding rank, or No data for posts GSC has nothing on (probably indexing or intent issues).

**Sort tricks:**
- Sort by **Δ ascending** → biggest drops at top (triage list).
- Sort by **Impr descending** → highest-leverage posts first (where work pays off most).
- Sort by **Pos ascending** within Page 2 → posts closest to Page 1 (overlaps with Striking Distance tab).

**"Movers only |Δ| ≥ 5" checkbox:** hides posts that didn't really move. Use during weekly review.

**Click any row** → opens the detail modal (trend chart + top queries + full weekly history).

---

### Movers — what changed and why

Three sections, all gated by the **Min impressions** selector at the top (default ≥500 — anything below that is noise on low-traffic posts).

1. **Fell off Page 1** — was Page 1 in the prior window, now isn't.
   - Highest priority. Open each one, check the modal chart: was it a sudden drop or gradual decay?
   - Sudden drop → check Recent Publishes, did you re-edit this post recently? Did a competitor publish? Algorithm update?
   - Gradual decay → content went stale, time to refresh.

2. **Rising (Δ ≤ -5)** — gained at least 5 positions.
   - Confirm what worked. If you updated it recently → log the pattern (which lever worked: title? content depth? new section?).
   - If you didn't update it → competitor moved, or Google reweighted intent. Note for future content.

3. **Bleeding (Δ ≥ +5)** — lost at least 5 positions but still in the same bucket as before (i.e. not the "Fell off P1" case).
   - Less urgent than Fell off P1 but still real. Open the modal and look at the position chart — is it a cliff or a slope?

**Gate tuning:** start at ≥500. If you see too few results, drop to ≥100 to surface long-tail movement. If too noisy, push to ≥1k or ≥5k.

---

### Striking Distance — what to optimize next

Posts ranking in **positions 11–20** with **≥500 impressions** in the selected window.

This is the single most actionable tab. These posts are *one good edit away* from Page 1, and they already have proven demand.

**How to read:** each row shows the post's current position, total impressions, and Δ.

**Priorities:**
1. **High impressions + positive Δ (Δ trending green ▲)** → Google likes the trajectory. Reinforce: add the keyword to H2s, expand the section that already ranks, add internal links pointing to it.
2. **High impressions + negative Δ** → being overtaken. Look at competitor pages — what do they have that you don't?
3. **High impressions + flat Δ (±0)** → stable Page 2. Needs a meaningful change (new section, updated stats, better intro) to break out.
4. **Low impressions** (you'll see these at the bottom) → less leverage, skip until you've worked the top of the list.

**Pair with the Queries tab:** for any striking-distance post, open the modal and check which specific queries are at 11–20. Those are the exact phrases your H2s and content should target.

---

### CTR Fixes — title/meta rewrites

Posts ranking on **Page 1** with **CTR < 1%** and **≥1k impressions**.

Page 1 with poor CTR = your title or meta description is failing in the SERP. The fix is **not** a content rewrite. The fix is a title/meta rewrite.

**How to triage:**
- Open the modal, look at the position chart. If position is solidly 1–5 and CTR is still under 1%, the SERP probably has rich features (featured snippet, People Also Ask, image pack) eating your clicks. Consider:
  - Rewriting the title to include a number, year, or curiosity hook.
  - Adding a question to the meta description.
  - Targeting the featured snippet directly (40–60 word answer paragraph at the top).
- If position is 6–10, push for rank improvement first (Striking Distance approach) — CTR at 7–10 is naturally low.

**Action gate:** only fix one title at a time per post, and wait 2–3 weeks to measure. Otherwise you can't tell which change worked.

---

### Queries — keyword-level investigation

Top ~25 queries per post by annual impressions (≥50 imp/year floor), with full weekly history and same window-aware aggregation as everything else.

**Use this tab when you need to know:**
- "What exact keywords does this post rank for?" → filter by post (dropdown), sort by impressions.
- "Which keywords are in striking distance, across all posts?" → check the "Striking distance only (pos 11–20)" toggle.
- "Which keywords lost ground?" → sort by Δ descending.
- "Which keywords have low CTR?" → sort by CTR ascending, filter by Page 1.

**Filters:**
- **Search box** matches query text, post title, or slug.
- **Post dropdown** isolates one post — combine with the Striking Distance toggle to see "which specific keywords on this post are at 11–20."
- **Bucket buttons** (Page 1 / Page 2 / Page 3+) toggle visibility — click to hide a bucket.
- **Min impr** gate filters out long-tail noise. Default 100.

**Render cap:** the table shows up to 500 rows per render. If your filter returns more, narrow it or use the CSV download.

**Inside any post's modal**, the "Top queries (selected window)" section shows that post's queries filtered to the selected window, sorted by impressions. This is usually where the real optimization signal lives.

---

### Recent Publishes — did my edits work?

Posts with an `updated:` or `date:` in the frontmatter from **April 2026 onward**, sorted most-recent-first.

The **Impact column** is the headline: it compares position over the **4 weeks immediately before** the activity date against the **4 weeks on/after** it.

**How to read the Impact:**
- `12.3 → 8.1 ▲ 4.2` (4w pre · 4w post) → Pre-edit rank was 12.3, post-edit rank is 8.1, improvement of 4.2 positions. The edit worked.
- `▼ X.X` → Edit made things worse. Look at what you changed and consider reverting.
- `±0` → No measurable impact yet. Either the edit was too small to matter or it's too soon (give it 4+ weeks).
- `post N.N · new — no pre data` → Brand new post, GSC has no history before publish. Wait 4+ weeks for a real comparison.
- `pre N.N · measuring` → Post was just edited; there isn't 1+ weeks of post-edit data yet.

**Action threshold:** if Impact is ▼ ≥3 positions on a meaningful-volume post (check impressions in the row's modal), revert or re-edit within the same week — easier than recovering later.

---

## Detail modal (opens when you click any row)

- **Top stats**: Position, Δ vs prior, Impressions, Clicks · CTR — all for the selected window.
- **Trend chart**: 52 weeks of history with the current window shaded blue and prior window shaded grey. Switch between Position / Impressions / Clicks / CTR with the buttons. Position chart is inverted so "up" on the chart = ranking better.
- **Top queries (selected window)**: query-level breakdown for this post over the selected window. Sorted by impressions. Open by default.
- **Weekly history table** (collapsed): every week of raw data. Click to expand if you need to dig.

---

## Glossary — what the numbers actually mean

**Position (Pos)** — impression-weighted average of the topmost rank the page held on each search where it appeared. Lower is better. A page-level position of 12 means *across every query the page ranked for*, blended by impressions. It is not the rank for any single keyword — use the Queries tab for that.

**Δ (delta)** — current window's Position minus prior window's Position.
- Negative Δ = rank improved (green ▲).
- Positive Δ = rank worsened (red ▼).
- `±0` is shown for |Δ| < 0.5.

**Prior window** — the same number of weeks immediately before the current window. E.g. if window = 4 weeks ending 2026-W18, prior = 2026-W11 to 2026-W14. Shown in the header's "vs prior" line.

**Bucket** — Page 1 = pos ≤10, Page 2 = 11–20, Page 3+ = >20, No data = no impressions in window.

**Impressions vs Clicks vs CTR** — exactly what GSC reports. CTR = clicks / impressions.

**Weighted Avg Position (Overview)** — across all posts, sum of (position × impressions) ÷ total impressions. A portfolio-level number, weighted toward your highest-volume posts.

**Striking distance** — positions 11–20. Defined by convention because they're typically one good edit away from Page 1 and already have search demand.

**"Fell off Page 1"** — was in Page 1 bucket in prior window, now in Page 2/3+ (but not No data). Treats "No data" specially since it usually means "no impressions" rather than a real drop.

---

## Weekly routine (15 minutes)

1. **Overview** — glance at the 3 portfolio KPIs. Anything more than ±15% → investigate.
2. **Movers → Fell off Page 1** at default gate (≥500). Triage each one (open modal, check chart shape, decide: edit / wait / no-op).
3. **Movers → Bleeding** at ≥500. Same triage.
4. **Striking Distance** sorted by impressions descending. Pick the top 1–2 posts to work on this week. Open the modal, find the queries at 11–20, plan the edit.
5. **CTR Fixes** if you haven't done a title pass in 4+ weeks.
6. **Recent Publishes** — look at the Impact column for posts you edited 4+ weeks ago. Confirm what worked (or didn't).

---

## Gotchas

- **GSC final-data lag**: the dashboard pulls only finalized data, which lags ~2 days. The "last refreshed" timestamp in the header is the cron run time; data inside is current to ~2 days before that.
- **Anonymized queries**: GSC withholds queries with very low impressions to protect privacy. The Queries tab can be missing the long tail.
- **Page-level avg position is a blend**: a page-level Position of 18 means "weighted across every keyword that page ranks for." It can hide the fact that your money keyword is at rank 4 while 50 long-tail terms drag the average down. Always check Queries for the real story.
- **Position vs traffic are decoupled**: rank improving but clicks falling can mean Google reweighted intent (your page is more relevant now to a less-searched query), a SERP feature took your clicks, or seasonality. Don't celebrate a rank gain that lost you traffic.
- **Sparkline auto-scales per row**: visually identical sparklines can mean very different absolute moves. Trust the `first → last` numbers under the sparkline.
- **Window changes apply globally**: switching from 4 to 52 weeks changes every number on every tab. The header's "vs prior" line shows you the actual comparison.
- **The Queries tab caps render at 500 rows**: if your filter returns more, narrow it or export CSV.
- **Brand-new posts show "no pre data" in Recent Publishes**: not a bug — GSC has no history before publish date. Wait 4+ weeks.
