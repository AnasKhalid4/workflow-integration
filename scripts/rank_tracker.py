"""
Daily Rank Tracker
==================
For every gig + keyword in config.json:

1. Searches Fiverr search results (page 1..N) and records on which page and
   at which position any of YOUR gigs appears for that keyword.
2. Searches DuckDuckGo for "site:fiverr.com <keyword>" and records whether
   your profile shows up (a proxy for external/Google visibility, which is
   a positive signal Fiverr cares about).

Results are appended to data/rank_history.csv (one row per keyword per day),
so over time you can see exactly which keywords you rank for and whether
your gig edits helped or hurt.

If Fiverr blocks the runner's IP that day, rows are saved as "BLOCKED"
instead of crashing. DuckDuckGo visibility usually still works.
"""

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

from bs4 import BeautifulSoup

from utils_fetch import make_session, get, polite_sleep

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
OUT_CSV = DATA_DIR / "rank_history.csv"

FIELDS = [
    "date",
    "gig_name",
    "keyword",
    "fiverr_status",      # FOUND / NOT_FOUND / BLOCKED / ERROR
    "fiverr_page",        # page number where found (1, 2, ...)
    "fiverr_position",    # position of the gig card on that page
    "ddg_status",         # FOUND / NOT_FOUND / BLOCKED / ERROR
    "ddg_position",       # position among DuckDuckGo results
]

# Matches gig-card style links like /username/some-gig-slug
GIG_LINK = re.compile(r"^/([A-Za-z0-9_]+)/([a-z0-9][a-z0-9\-]*)$")

# Path segments that look like /xxx/yyy but are NOT seller gigs
NOT_SELLERS = {
    "categories", "search", "support", "community", "stories", "resources",
    "cp", "pages", "terms_of_service", "logo-maker", "pro", "hire", "gigs",
    "legal-portal", "news", "partnerships", "jobs", "about-us", "start_selling",
}


def gig_cards_in_order(html):
    """
    Heuristic parser: return an ordered, de-duplicated list of
    (username, slug) pairs for gig cards found in a Fiverr search page.
    Gig-card links on search pages carry a context query string, which we
    use to filter out navigation links.
    """
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    ordered = []
    for a in soup.find_all("a", href=True):
        parsed = urlparse(a["href"])
        # search-result gig cards carry ?context... query params; nav links don't
        qs_keys = parse_qs(parsed.query).keys()
        if not any(k == "context" or k.startswith("context_") for k in qs_keys):
            continue
        m = GIG_LINK.match(parsed.path)
        if not m:
            continue
        user, slug = m.group(1).lower(), m.group(2)
        if user in NOT_SELLERS:
            continue
        key = (user, slug)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def fiverr_rank(session, keyword, username, pages_to_check):
    """Where does any of the user's gigs appear in Fiverr search for keyword?"""
    username = username.lower()
    for page in range(1, pages_to_check + 1):
        url = f"https://www.fiverr.com/search/gigs?query={quote_plus(keyword)}&page={page}"
        status, code, html = get(session, url)
        if status != "OK":
            return status, "", ""
        cards = gig_cards_in_order(html)
        for pos, (user, _slug) in enumerate(cards, start=1):
            if user == username:
                return "FOUND", str(page), str(pos)
        polite_sleep()
    return "NOT_FOUND", "", ""


def ddg_rank(session, keyword, username):
    """Does the seller's Fiverr profile appear in DuckDuckGo for this keyword?"""
    q = quote_plus(f"site:fiverr.com {keyword}")
    url = f"https://html.duckduckgo.com/html/?q={q}"
    status, code, html = get(session, url)
    if status != "OK":
        return status, ""
    soup = BeautifulSoup(html, "lxml")
    anchors = soup.select("a.result__a") or soup.find_all("a", href=True)
    needle = f"fiverr.com/{username.lower()}"
    for pos, a in enumerate(anchors, start=1):
        href = unquote(a.get("href", "")).lower()
        if needle in href:
            return "FOUND", str(pos)
    return "NOT_FOUND", ""


def main():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    username = config["fiverr_username"]
    pages = int(config.get("search_pages_to_check", 2))

    session = make_session()
    today = date.today().isoformat()
    new_rows = []

    for gig in config["gigs"]:
        for kw in gig["keywords"]:
            f_status, f_page, f_pos = fiverr_rank(session, kw, username, pages)
            polite_sleep()
            d_status, d_pos = ddg_rank(session, kw, username)
            polite_sleep(1.5, 3.0)
            row = {
                "date": today,
                "gig_name": gig["name"],
                "keyword": kw,
                "fiverr_status": f_status,
                "fiverr_page": f_page,
                "fiverr_position": f_pos,
                "ddg_status": d_status,
                "ddg_position": d_pos,
            }
            new_rows.append(row)
            print(
                f"[{gig['name']}] '{kw}'  fiverr={f_status} "
                f"{('p' + f_page + ' #' + f_pos) if f_status == 'FOUND' else ''}  "
                f"ddg={d_status} {('#' + d_pos) if d_status == 'FOUND' else ''}"
            )

    write_header = not OUT_CSV.exists()
    with OUT_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    blocked = sum(1 for r in new_rows if r["fiverr_status"] == "BLOCKED")
    if blocked == len(new_rows) and new_rows:
        print(
            "\nNOTE: Fiverr blocked all requests today (normal for datacenter "
            "IPs). DuckDuckGo columns may still have data. Will retry tomorrow."
        )
    print(f"\nSaved {len(new_rows)} rows to {OUT_CSV}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
