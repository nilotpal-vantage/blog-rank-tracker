#!/usr/bin/env python3
"""
update-data.py — Refresh blog rank tracker data from Google Search Console.

Reads posts from _posts.json, queries GSC for:
  - Current period (last 28d, ending 1d ago for finalized data)
  - Previous period (28d before that)
  - Weekly history (last 12 weeks, grouped by week+page)

Writes:
  - data.js     (post metadata: title, slug, url, tags, date, updated)
  - rankings.js (GSC metrics: position, prev_position, delta, impressions,
                 clicks, ctr, bucket, history[])

Usage:
  python3 update-data.py

Auth comes from ../../gsc-mcp/gsc_tokens.db (existing OAuth stored creds).
"""

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

POSTS_JSON = HERE / "_posts.json"
DATA_JS = HERE / "data.js"
RANKINGS_JS = HERE / "rankings.js"


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
        title_m = re.search(r'^title:\s*"(.+?)"', fm, re.M)
        slug_m = re.search(r'^slug:\s*"(.+?)"', fm, re.M)
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
    # Anchor on /en/blog/<slug>/  to avoid accidental partial matches
    parts = "|".join(s.replace(".", r"\.") for s in slugs)
    return f"/en/blog/({parts})/?$"


def query_pages(service, start: str, end: str, regex: str) -> list[dict]:
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["page"],
        "dimensionFilterGroups": [
            {
                "filters": [
                    {"dimension": "page", "operator": "includingRegex", "expression": regex}
                ]
            }
        ],
        "rowLimit": 25000,
        "dataState": "final",
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    return resp.get("rows", [])


def query_weekly(service, start: str, end: str, regex: str) -> list[dict]:
    body = {
        "startDate": start,
        "endDate": end,
        "dimensions": ["date", "page"],
        "dimensionFilterGroups": [
            {
                "filters": [
                    {"dimension": "page", "operator": "includingRegex", "expression": regex}
                ]
            }
        ],
        "rowLimit": 25000,
        "dataState": "final",
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    return resp.get("rows", [])


# ─── Build data ────────────────────────────────────────────────────────────
def slug_from_url(url: str) -> str:
    # Strip prefix and trailing slash
    s = url.replace(BLOG_PREFIX, "").rstrip("/")
    return s


def bucket(pos: float) -> str:
    if pos <= 10:
        return "page1"
    if pos <= 20:
        return "page2"
    return "page3+"


def main():
    print("Extracting posts from Astro repo…")
    posts = extract_posts()
    POSTS_JSON.write_text(json.dumps(posts, indent=2, ensure_ascii=False))
    slugs = [p["slug"] for p in posts]
    print(f"  {len(slugs)} posts authored by '{AUTHOR_MATCH}'")

    today = datetime.utcnow().date()
    # GSC has ~2-day lag for finalized data; end period 1 day ago
    cur_end = today - timedelta(days=1)
    cur_start = cur_end - timedelta(days=27)  # 28-day window inclusive
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=27)
    hist_start = cur_end - timedelta(days=83)  # 12 weeks = 84 days

    print(f"Current: {cur_start} → {cur_end}")
    print(f"Previous: {prev_start} → {prev_end}")
    print(f"History: {hist_start} → {cur_end}")

    regex = build_slug_regex(slugs)
    svc = gsc()

    print("Querying current period…")
    cur_rows = query_pages(svc, cur_start.isoformat(), cur_end.isoformat(), regex)
    print(f"  {len(cur_rows)} rows")

    print("Querying previous period…")
    prev_rows = query_pages(svc, prev_start.isoformat(), prev_end.isoformat(), regex)
    print(f"  {len(prev_rows)} rows")

    print("Querying weekly history…")
    hist_rows = query_weekly(svc, hist_start.isoformat(), cur_end.isoformat(), regex)
    print(f"  {len(hist_rows)} rows")

    # ─── Index by slug ───
    cur_by_slug = {}
    for r in cur_rows:
        url = r["keys"][0]
        s = slug_from_url(url)
        cur_by_slug[s] = {
            "position": round(r["position"], 2),
            "impressions": r["impressions"],
            "clicks": r["clicks"],
            "ctr": round(r["ctr"], 4),
        }

    prev_by_slug = {}
    for r in prev_rows:
        url = r["keys"][0]
        s = slug_from_url(url)
        prev_by_slug[s] = {
            "position": round(r["position"], 2),
            "impressions": r["impressions"],
            "clicks": r["clicks"],
            "ctr": round(r["ctr"], 4),
        }

    # Roll daily history into weekly buckets per slug
    # Week key: ISO year-week, e.g. "2026-W17"
    hist_by_slug = {}
    for r in hist_rows:
        date_str, url = r["keys"]
        s = slug_from_url(url)
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        iso = d.isocalendar()
        wk = f"{iso[0]}-W{iso[1]:02d}"
        if s not in hist_by_slug:
            hist_by_slug[s] = {}
        if wk not in hist_by_slug[s]:
            hist_by_slug[s][wk] = {"pos_sum": 0.0, "imp_sum": 0, "n": 0}
        # Weighted by impressions for accurate avg position
        b = hist_by_slug[s][wk]
        b["pos_sum"] += r["position"] * r["impressions"]
        b["imp_sum"] += r["impressions"]
        b["n"] += 1

    # ─── Combine into final records ───
    records = []
    for p in posts:
        s = p["slug"]
        cur = cur_by_slug.get(s, {})
        prev = prev_by_slug.get(s, {})
        cur_pos = cur.get("position")
        prev_pos = prev.get("position")
        delta = None
        if cur_pos is not None and prev_pos is not None:
            # Negative delta = improvement (position dropped from 15 to 8 = -7 = good)
            delta = round(cur_pos - prev_pos, 2)
        history = []
        if s in hist_by_slug:
            for wk in sorted(hist_by_slug[s].keys()):
                b = hist_by_slug[s][wk]
                avg = b["pos_sum"] / b["imp_sum"] if b["imp_sum"] > 0 else None
                history.append({"w": wk, "p": round(avg, 2) if avg else None})
        records.append({
            "title": p["title"],
            "slug": s,
            "url": BLOG_PREFIX + s + "/",
            "date": p["date"],
            "updated": p["updated"],
            "tags": p["tags"],
            "position": cur_pos,
            "prev_position": prev_pos,
            "delta": delta,
            "impressions": cur.get("impressions", 0),
            "clicks": cur.get("clicks", 0),
            "ctr": cur.get("ctr", 0.0),
            "bucket": bucket(cur_pos) if cur_pos is not None else "no-data",
            "prev_bucket": bucket(prev_pos) if prev_pos is not None else "no-data",
            "history": history,
        })

    # ─── Write JS files ───
    meta = {
        "current_start": cur_start.isoformat(),
        "current_end": cur_end.isoformat(),
        "previous_start": prev_start.isoformat(),
        "previous_end": prev_end.isoformat(),
        "history_start": hist_start.isoformat(),
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

    # Summary
    matched = sum(1 for r in records if r["position"] is not None)
    p1 = sum(1 for r in records if r["bucket"] == "page1")
    p2 = sum(1 for r in records if r["bucket"] == "page2")
    p3 = sum(1 for r in records if r["bucket"] == "page3+")
    nodata = sum(1 for r in records if r["bucket"] == "no-data")
    fell_off = sum(
        1 for r in records
        if r["prev_bucket"] == "page1" and r["bucket"] in ("page2", "page3+")
    )
    print()
    print(f"Matched in GSC : {matched} / {len(records)}")
    print(f"  page1        : {p1}")
    print(f"  page2        : {p2}")
    print(f"  page3+       : {p3}")
    print(f"  no-data      : {nodata}")
    print(f"Fell off page1 : {fell_off}")
    print(f"Wrote {DATA_JS.name} ({DATA_JS.stat().st_size} bytes)")
    print(f"Wrote {RANKINGS_JS.name} ({RANKINGS_JS.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
