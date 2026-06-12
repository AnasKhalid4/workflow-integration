"""
Shared fetch helpers for all scripts.

Tries `cloudscraper` first (it can pass some Cloudflare checks).
Falls back to plain `requests` if cloudscraper is unavailable.

IMPORTANT / HONEST NOTE:
Fiverr aggressively blocks datacenter IPs (like GitHub Actions runners).
Some days requests will be blocked. Scripts log those rows as "BLOCKED"
instead of failing, so the rest of the automation keeps working.
This tool only reads PUBLIC pages. It never logs in to Fiverr and never
fakes online status (that would violate Fiverr's Terms of Service).
"""

import random
import time

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}

BLOCK_MARKERS = (
    "cf-challenge",
    "just a moment",
    "attention required",
    "access denied",
    "captcha",
    "px-captcha",
    "perimeterx",
)


def make_session():
    """Return a cloudscraper session if possible, else a requests session."""
    try:
        import cloudscraper

        return cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
    except Exception:
        import requests

        s = requests.Session()
        s.headers.update(HEADERS)
        return s


def get(session, url, timeout=30):
    """
    Fetch a URL.

    Returns a tuple: (status_label, http_code, text)
      status_label is one of: "OK", "BLOCKED", "ERROR"
    """
    try:
        r = session.get(url, headers=HEADERS, timeout=timeout)
        sample = (r.text or "")[:5000].lower()
        if r.status_code in (403, 429, 503) or any(m in sample for m in BLOCK_MARKERS):
            return "BLOCKED", r.status_code, r.text or ""
        if r.status_code != 200:
            return "ERROR", r.status_code, r.text or ""
        return "OK", 200, r.text or ""
    except Exception as e:  # network errors, timeouts, etc.
        return "ERROR", 0, str(e)


def polite_sleep(low=3.0, high=6.5):
    """Random delay between requests so we behave like a polite visitor."""
    time.sleep(random.uniform(low, high))
