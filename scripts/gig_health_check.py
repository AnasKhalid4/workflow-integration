"""
Gig Health Check
================
Fetches each gig page and records:
- whether the gig is live (HTTP 200 and gig title present)
- rating value / rating count when Fiverr exposes them in the page JSON

Why this matters: gigs silently going "under review", denied, or paused is a
common cause of impressions dropping to literally zero. This check gives you
an early warning the same day it happens.

Appends one row per gig per day to data/gig_health.csv.
"""

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

from utils_fetch import make_session, get, polite_sleep

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
OUT_CSV = DATA_DIR / "gig_health.csv"

FIELDS = ["date", "gig_name", "status", "http_code", "title_found", "rating", "reviews"]

RATING_RE = re.compile(r'"rating(?:Value)?"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)"?')
REVIEWS_RE = re.compile(r'"(?:ratingsCount|ratingCount|reviews_count)"\s*:\s*"?(\d+)"?')


def check_gig(session, gig):
    status, code, html = get(session, gig["url"])
    title_found = ""
    rating = ""
    reviews = ""
    if status == "OK":
        low = html.lower()
        # The gig slug words should appear in the page if the gig is live.
        slug_words = gig["url"].rstrip("/").split("/")[-1].split("-")[:4]
        title_found = "yes" if all(w in low for w in slug_words if len(w) > 3) else "unsure"
        m = RATING_RE.search(html)
        if m:
            rating = m.group(1)
        m = REVIEWS_RE.search(html)
        if m:
            reviews = m.group(1)
    return {
        "date": date.today().isoformat(),
        "gig_name": gig["name"],
        "status": status,           # OK / BLOCKED / ERROR
        "http_code": str(code),
        "title_found": title_found, # yes / unsure / "" when blocked
        "rating": rating,
        "reviews": reviews,
    }


def main():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    session = make_session()

    rows = []
    for gig in config["gigs"]:
        row = check_gig(session, gig)
        rows.append(row)
        print(f"[{row['gig_name']}] status={row['status']} http={row['http_code']} "
              f"title_found={row['title_found']} rating={row['rating'] or '-'} "
              f"reviews={row['reviews'] or '-'}")
        polite_sleep()

    write_header = not OUT_CSV.exists()
    with OUT_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} rows to {OUT_CSV}")

    # Loud warning in the Actions log if a gig looks dead while others are fine
    dead = [r for r in rows if r["status"] == "OK" and r["title_found"] != "yes"]
    if dead:
        print("\n*** WARNING: these gigs returned a page but the gig content was "
              "not clearly found. Check they are not paused/denied/under review: "
              + ", ".join(r["gig_name"] for r in dead))
    return 0


if __name__ == "__main__":
    sys.exit(main())
