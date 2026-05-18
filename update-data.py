#!/usr/bin/env python3
"""
update-data.py — Refresh blog rank tracker data from Google Search Console.

Pulls 52 weeks of weekly per-page metrics (position, impressions, clicks, CTR)
for posts authored by Nilotpal in the local Astro repo.

The dashboard computes any-window comparisons in JS from this history,
so this script doesn't pre-compute current/previous deltas.

Writes:
  - data.js     (metadata: history range, generated_at, post_count)
  - rankings.js (per-post: title, slug, url, tags, history[{w,p,i,c,ctr}])

Usage:
  python3 update-data.py

Auth comes from ../../gsc-mcp/gsc_tokens.db (existing OAuth stored creds).
"""

import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build

# ─── Config ────────────────────────────────────────────────────────────────
HERE = Path(__file__).parent
DB_PATH = HERE.parent.parent / "gsc-mcp" / "gsc_tokens.db"
USER_ID = "P7O7sl4cUK26l4MDD99ILXWqnDA"
SITE_URL = "https://www.vantagecircle.com/"
BLOG_PREFIX = "https://www.vantagecircle.com/en/blog/"
POSTS_DIR = HERE.parent.parent / "vantagecircle-astro" / "content" / "en" / "posts"
AUTHOR_MATCH = "nilotpal"  # case-insensitive substring match in author field
HISTORY_DAYS = 364  # 52 weeks

# Slugs to exclude from the tracker (posts the user is no longer working on).
EXCLUDED_SLUGS = {
    "employee-onboarding-survey-questions",
    "employee-retention-survey-questions",
    "employee-satisfaction-survey",
    "pulse-surveys",
}

POSTS_JSON = HERE / "_posts.json"
DATA_JS = HERE / "data.js"
RANKINGS_JS = HERE / "rankings.js"
QUERIES_JS = HERE / "queries.js"
INDEX_HTML = HERE / "index.html"
TARGET_KEYWORDS_JSON = HERE / "target_keywords.json"

# How many top queries to keep per post (by total annual impressions).
QUERIES_TOP_N = 25
# Drop queries below this annual impression count to suppress long-tail noise.
QUERIES_MIN_IMP = 50


# ─── Extract posts from Astro repo ────────────────────────────────────────
def extract_posts() -> list[dict]:
    if not POSTS_DIR.exists():
        sys.exit(f"Posts dir not found: {POSTS_DIR}")
    posts = []
    for fp in sorted(POSTS_DIR.iterdir()):
        if fp.suffix != ".md":
            continue
        content = fp.read_text(encoding="utf-8")[:8000]
        m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not m:
            continue
        fm = m.group(1)
        author_m = re.search(r"^author:\s*(.+)", fm, re.M)
        if not author_m or AUTHOR_MATCH not in author_m.group(1).lower():
            continue
        slug_m_check = re.search(r'^slug:\s*"(.+?)"', fm, re.M)
        slug_check = slug_m_check.group(1) if slug_m_check else fp.stem
        if slug_check in EXCLUDED_SLUGS:
            continue
        if slug_check.endswith("-draft"):
            continue
        title_m = re.search(r'^title:\s*"(.+?)"', fm, re.M)
        slug_m = slug_m_check
        date_m = re.search(r"^date:\s*(\S+)", fm, re.M)
        updated_m = re.search(r"^updated:\s*(\S+)", fm, re.M)
        tags_section = re.search(r"^tags:\s*\n((?:\s+-\s+.+\n)*)", fm, re.M)
        tags = []
        if tags_section:
            tags = [t.strip().lstrip("- ") for t in tags_section.group(1).strip().split("\n") if t.strip()]
        posts.append({
            "title": title_m.group(1) if title_m else "",
            "slug": slug_m.group(1) if slug_m else fp.stem,
            "date": date_m.group(1) if date_m else "",
            "updated": updated_m.group(1) if updated_m else "",
            "tags": tags,
        })
    return posts


# ─── Auth ──────────────────────────────────────────────────────────────────
def get_credentials() -> Credentials:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT credentials FROM users WHERE id = ? AND is_active = 1", (USER_ID,)
    ).fetchone()
    conn.close()
    if not row:
        sys.exit("No stored credentials. Run OAuth flow first.")
    cd = json.loads(row["credentials"])
    creds = Credentials(
        token=cd["token"],
        refresh_token=cd.get("refresh_token"),
        token_uri=cd["token_uri"],
        client_id=cd["client_id"],
        client_secret=cd["client_secret"],
        scopes=cd["scopes"],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        cd["token"] = creds.token
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute(
            "UPDATE users SET credentials = ? WHERE id = ?", (json.dumps(cd), USER_ID)
        )
        conn.commit()
        conn.close()
    return creds


def gsc():
    return build("searchconsole", "v1", credentials=get_credentials())


# ─── Query helpers ─────────────────────────────────────────────────────────
def build_slug_regex(slugs: list[str]) -> str:
    parts = "|".join(s.replace(".", r"\.") for s in slugs)
    return f"/en/blog/({parts})/?$"


PAGE_LIMIT = 25000  # GSC API max


def query_daily_paginated(service, start: str, end: str, regex: str) -> list[dict]:
    """Pull date+page rows, paginating to handle >25k results."""
    rows = []
    start_row = 0
    while True:
        body = {
            "startDate": start,
            "endDate": end,
            "dimensions": ["date", "page"],
            "dimensionFilterGroups": [
                {"filters": [{"dimension": "page", "operator": "includingRegex", "expression": regex}]}
            ],
            "rowLimit": PAGE_LIMIT,
            "startRow": start_row,
            "dataState": "final",
        }
        resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
        chunk = resp.get("rows", [])
        rows.extend(chunk)
        print(f"  page {start_row // PAGE_LIMIT + 1}: +{len(chunk)} rows (total {len(rows)})")
        if len(chunk) < PAGE_LIMIT:
            break
        start_row += PAGE_LIMIT
    return rows


def query_with_queries_paginated(service, start: str, end: str, regex: str) -> list[dict]:
    """Pull date+page+query rows. GSC returns at most 25k per page, so paginate."""
    rows = []
    start_row = 0
    while True:
        body = {
            "startDate": start,
            "endDate": end,
            "dimensions": ["date", "page", "query"],
            "dimensionFilterGroups": [
                {"filters": [{"dimension": "page", "operator": "includingRegex", "expression": regex}]}
            ],
            "rowLimit": PAGE_LIMIT,
            "startRow": start_row,
            "dataState": "final",
        }
        resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
        chunk = resp.get("rows", [])
        rows.extend(chunk)
        print(f"  page {start_row // PAGE_LIMIT + 1}: +{len(chunk)} rows (total {len(rows)})")
        if len(chunk) < PAGE_LIMIT:
            break
        start_row += PAGE_LIMIT
    return rows


def slug_from_url(url: str) -> str:
    return url.replace(BLOG_PREFIX, "").rstrip("/")


def load_target_keywords() -> dict[str, str]:
    """Slug -> target keyword. Ignores keys starting with '_' (e.g. _comment)."""
    if not TARGET_KEYWORDS_JSON.exists():
        return {}
    raw = json.loads(TARGET_KEYWORDS_JSON.read_text())
    return {k: v for k, v in raw.items() if not k.startswith("_") and isinstance(v, str)}


def history_from_wkmap(wkmap: dict) -> list[dict]:
    """Convert a {week: {pos_imp_sum, imp, clicks}} dict to sorted history entries."""
    out = []
    for wk in sorted(wkmap.keys()):
        b = wkmap[wk]
        pos = b["pos_imp_sum"] / b["imp"] if b["imp"] > 0 else None
        ctr = b["clicks"] / b["imp"] if b["imp"] > 0 else 0
        out.append({
            "w": wk,
            "p": round(pos, 2) if pos is not None else None,
            "i": b["imp"],
            "c": b["clicks"],
            "ctr": round(ctr, 4),
        })
    return out


def resolve_target(slug: str, target_keywords: dict, slug_qhist: dict) -> tuple[str | None, str, list[dict]]:
    """Return (target_keyword, source, target_history) for a slug.

    source = "manual" if defined in target_keywords.json (even when GSC has no data
    for that query — the empty history is the honest signal).
    source = "auto" when we fall back to the top query by total impressions.
    source = "none" when there's no query data at all to fall back to.
    """
    if slug in target_keywords:
        kw = target_keywords[slug]
        wkmap = slug_qhist.get(kw, {})
        return kw, "manual", history_from_wkmap(wkmap)
    if not slug_qhist:
        return None, "none", []
    best_kw = max(
        slug_qhist.keys(),
        key=lambda q: sum(b["imp"] for b in slug_qhist[q].values()),
    )
    return best_kw, "auto", history_from_wkmap(slug_qhist[best_kw])


def main():
    print("Extracting posts from Astro repo…")
    posts = extract_posts()
    POSTS_JSON.write_text(json.dumps(posts, indent=2, ensure_ascii=False))
    slugs = [p["slug"] for p in posts]
    print(f"  {len(slugs)} posts authored by '{AUTHOR_MATCH}'")

    today = datetime.utcnow().date()
    end = today - timedelta(days=1)  # GSC has ~2-day lag for finalized data
    start = end - timedelta(days=HISTORY_DAYS - 1)

    print(f"History window: {start} → {end} ({HISTORY_DAYS} days)")

    regex = build_slug_regex(slugs)
    svc = gsc()

    target_keywords = load_target_keywords()
    print(f"  {len(target_keywords)} manual target keywords loaded from target_keywords.json")

    print("Querying daily-by-page (paginated)…")
    rows = query_daily_paginated(svc, start.isoformat(), end.isoformat(), regex)

    # ─── Roll daily into ISO weeks per slug ─────────────────────────────
    # Each weekly bucket: impression-weighted position avg, summed impressions/clicks
    hist_by_slug: dict[str, dict[str, dict]] = {}
    for r in rows:
        date_str, url = r["keys"]
        s = slug_from_url(url)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        iso = d.isocalendar()
        wk = f"{iso[0]}-W{iso[1]:02d}"
        if s not in hist_by_slug:
            hist_by_slug[s] = {}
        if wk not in hist_by_slug[s]:
            hist_by_slug[s][wk] = {"pos_imp_sum": 0.0, "imp": 0, "clicks": 0}
        b = hist_by_slug[s][wk]
        b["pos_imp_sum"] += r["position"] * r["impressions"]
        b["imp"] += r["impressions"]
        b["clicks"] += r["clicks"]

    # ─── Query-level pull ──────────────────────────────────────────────
    # Pulled before building records so each record can carry a target-keyword
    # history aggregated from the (slug, query) breakdown.
    print("Querying date+page+query (paginated)…")
    qrows = query_with_queries_paginated(svc, start.isoformat(), end.isoformat(), regex)

    # Bucket into ISO weeks per (slug, query). Anonymized queries come back as ""
    # in the GSC response — skip those.
    qhist: dict[str, dict[str, dict[str, dict]]] = {}
    for r in qrows:
        date_str, url, q = r["keys"]
        if not q:
            continue
        s = slug_from_url(url)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        iso = d.isocalendar()
        wk = f"{iso[0]}-W{iso[1]:02d}"
        qhist.setdefault(s, {}).setdefault(q, {}).setdefault(
            wk, {"pos_imp_sum": 0.0, "imp": 0, "clicks": 0}
        )
        b = qhist[s][q][wk]
        b["pos_imp_sum"] += r["position"] * r["impressions"]
        b["imp"] += r["impressions"]
        b["clicks"] += r["clicks"]

    # ─── Build records ─────────────────────────────────────────────────
    records = []
    for p in posts:
        s = p["slug"]
        history = history_from_wkmap(hist_by_slug.get(s, {}))
        target_kw, target_source, target_history = resolve_target(
            s, target_keywords, qhist.get(s, {})
        )
        records.append({
            "title": p["title"],
            "slug": s,
            "url": BLOG_PREFIX + s + "/",
            "date": p["date"],
            "updated": p["updated"],
            "tags": p["tags"],
            "history": history,
            "target_keyword": target_kw,
            "target_source": target_source,
            "target_history": target_history,
        })

    # ─── Write JS files ────────────────────────────────────────────────
    all_weeks = sorted({h["w"] for r in records for h in r["history"]})
    meta = {
        "history_start": start.isoformat(),
        "history_end": end.isoformat(),
        "history_days": HISTORY_DAYS,
        "first_week": all_weeks[0] if all_weeks else None,
        "last_week": all_weeks[-1] if all_weeks else None,
        "all_weeks": all_weeks,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "post_count": len(records),
    }

    DATA_JS.write_text(
        "// Auto-generated. Do not edit.\n"
        f"const META = {json.dumps(meta, indent=2)};\n"
    )
    RANKINGS_JS.write_text(
        "// Auto-generated. Do not edit.\n"
        f"const RANKINGS = {json.dumps(records, indent=2, ensure_ascii=False)};\n"
    )

    # Build QUERIES = { slug: [{q, ti, tc, h: [...]}, ...] } keeping top N per slug.
    queries_out: dict[str, list[dict]] = {}
    for s, qmap in qhist.items():
        ranked = []
        for q, wkmap in qmap.items():
            total_i = sum(b["imp"] for b in wkmap.values())
            total_c = sum(b["clicks"] for b in wkmap.values())
            if total_i < QUERIES_MIN_IMP:
                continue
            history = []
            for wk in sorted(wkmap.keys()):
                b = wkmap[wk]
                pos = b["pos_imp_sum"] / b["imp"] if b["imp"] > 0 else None
                ctr = b["clicks"] / b["imp"] if b["imp"] > 0 else 0
                history.append({
                    "w": wk,
                    "p": round(pos, 2) if pos is not None else None,
                    "i": b["imp"],
                    "c": b["clicks"],
                    "ctr": round(ctr, 4),
                })
            ranked.append({"q": q, "ti": total_i, "tc": total_c, "h": history})
        ranked.sort(key=lambda x: x["ti"], reverse=True)
        queries_out[s] = ranked[:QUERIES_TOP_N]

    # Compact JSON — queries.js is large enough that pretty-printing doubles it.
    QUERIES_JS.write_text(
        "// Auto-generated. Do not edit.\n"
        f"const QUERIES = {json.dumps(queries_out, separators=(',', ':'), ensure_ascii=False)};\n"
    )

    # ─── Cache-bust the script tags in index.html ──────────────────────
    if INDEX_HTML.exists():
        digest = hashlib.md5(
            DATA_JS.read_bytes() + RANKINGS_JS.read_bytes() + QUERIES_JS.read_bytes()
        ).hexdigest()[:10]
        html = INDEX_HTML.read_text()
        new_html = re.sub(r'src="data\.js(\?[^"]*)?"', f'src="data.js?v={digest}"', html)
        new_html = re.sub(r'src="rankings\.js(\?[^"]*)?"', f'src="rankings.js?v={digest}"', new_html)
        new_html = re.sub(r'src="queries\.js(\?[^"]*)?"', f'src="queries.js?v={digest}"', new_html)
        if new_html != html:
            INDEX_HTML.write_text(new_html)
            print(f"Cache-bust: data version = {digest}")

    # ─── Summary ───────────────────────────────────────────────────────
    matched = sum(1 for r in records if r["history"])
    print()
    print(f"Posts with GSC data : {matched} / {len(records)}")
    print(f"Weeks covered       : {len(all_weeks)} ({all_weeks[0] if all_weeks else '—'} → {all_weeks[-1] if all_weeks else '—'})")
    print(f"Wrote {DATA_JS.name} ({DATA_JS.stat().st_size:,} bytes)")
    print(f"Wrote {RANKINGS_JS.name} ({RANKINGS_JS.stat().st_size:,} bytes)")
    print(f"Wrote {QUERIES_JS.name} ({QUERIES_JS.stat().st_size:,} bytes) — {sum(len(v) for v in queries_out.values())} queries across {len(queries_out)} posts")


if __name__ == "__main__":
    main()
