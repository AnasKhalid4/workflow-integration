"""
Weekly Report Generator
=======================
Reads the CSVs collected by the daily tracker plus your manually-logged
Fiverr dashboard stats (data/manual_stats.csv) and writes a Markdown report:

- reports/LATEST.md                (always overwritten)
- reports/WEEKLY_REPORT_<date>.md  (archived copy)

The weekly GitHub Action also posts the report as a GitHub Issue so you get
it by email.
"""

import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def read_csv(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fmt_fiverr(row):
    if row["fiverr_status"] == "FOUND":
        return f"page {row['fiverr_page']}, #{row['fiverr_position']}"
    return row["fiverr_status"].lower()


def fmt_ddg(row):
    if row["ddg_status"] == "FOUND":
        return f"#{row['ddg_position']}"
    return row["ddg_status"].lower()


def build_ranking_section(rank_rows):
    if not rank_rows:
        return ("_No ranking data yet. Run the **Daily Rank Tracker** workflow "
                "(Actions tab -> Run workflow) to start collecting._\n")

    latest_date = max(r["date"] for r in rank_rows)
    week_ago = (datetime.fromisoformat(latest_date) - timedelta(days=6)).date().isoformat()

    latest = {}
    older = {}
    for r in rank_rows:
        key = (r["gig_name"], r["keyword"])
        if r["date"] == latest_date:
            latest[key] = r
        if r["date"] <= week_ago:
            older[key] = r  # keeps overwriting -> closest date before the window

    lines = [
        f"Latest data: **{latest_date}**\n",
        "| Gig | Keyword | Fiverr search now | ~7 days ago | DuckDuckGo |",
        "|---|---|---|---|---|",
    ]
    for key in sorted(latest):
        now = latest[key]
        before = older.get(key)
        lines.append(
            f"| {key[0]} | {key[1]} | {fmt_fiverr(now)} | "
            f"{fmt_fiverr(before) if before else '-'} | {fmt_ddg(now)} |"
        )

    blocked_days = len({r["date"] for r in rank_rows if r["fiverr_status"] == "BLOCKED"})
    if blocked_days:
        lines.append(
            f"\n_Fiverr blocked the tracker on {blocked_days} day(s) "
            "(normal for datacenter IPs - those rows say 'blocked')._"
        )
    lines.append(
        "\n**How to read this:** 'not_found' on page 1-2 means buyers are not "
        "seeing you for that keyword - either change the keyword in "
        "`config.json` to something less competitive, or improve the gig that "
        "targets it. Any FOUND keyword is gold: be online when buyers search."
    )
    return "\n".join(lines) + "\n"


def build_health_section(health_rows):
    if not health_rows:
        return "_No gig health data yet._\n"
    latest_date = max(r["date"] for r in health_rows)
    latest = [r for r in health_rows if r["date"] == latest_date]
    lines = [
        f"Checked: **{latest_date}**\n",
        "| Gig | Live? | Rating | Reviews |",
        "|---|---|---|---|",
    ]
    for r in latest:
        if r["status"] == "OK" and r["title_found"] == "yes":
            live = "yes"
        elif r["status"] == "BLOCKED":
            live = "blocked (unknown)"
        else:
            live = "CHECK MANUALLY"
        lines.append(f"| {r['gig_name']} | {live} | {r['rating'] or '-'} | {r['reviews'] or '-'} |")
    return "\n".join(lines) + "\n"


def build_manual_stats_section(stat_rows):
    if not stat_rows:
        return ("_No dashboard stats logged yet. Each week, open Fiverr -> "
                "Gigs -> stats and add a row per gig to `data/manual_stats.csv`._\n")
    # keep the last 8 rows per gig
    by_gig = {}
    for r in stat_rows:
        by_gig.setdefault(r["gig_name"], []).append(r)
    lines = [
        "| Week | Gig | Impressions | Clicks | CTR | Messages | Orders |",
        "|---|---|---|---|---|---|---|",
    ]
    advice = []
    for gig, rows in by_gig.items():
        rows = sorted(rows, key=lambda r: r["week_start_date"])[-8:]
        for r in rows:
            try:
                imp = int(r["impressions"]); clk = int(r["clicks"])
                ctr = f"{(clk / imp * 100):.1f}%" if imp else "-"
            except (ValueError, ZeroDivisionError):
                imp, clk, ctr = r["impressions"], r["clicks"], "-"
            lines.append(
                f"| {r['week_start_date']} | {gig} | {r['impressions']} | "
                f"{r['clicks']} | {ctr} | {r['messages']} | {r['orders']} |"
            )
        last = rows[-1]
        try:
            imp = int(last["impressions"]); clk = int(last["clicks"]); msg = int(last["messages"])
            if imp == 0:
                advice.append(f"- **{gig}**: 0 impressions -> a search/visibility problem. "
                              "Check the gig is active, improve title keywords + tags, "
                              "and confirm it appears when you search its exact title in incognito.")
            elif imp > 0 and clk / imp < 0.015:
                advice.append(f"- **{gig}**: people see it but don't click (CTR < 1.5%) -> "
                              "thumbnail, title, or starting price problem.")
            elif clk > 0 and msg == 0:
                advice.append(f"- **{gig}**: clicks but no messages -> description/proof problem. "
                              "Add a video, portfolio links, and a clear 'message me first' CTA.")
        except (ValueError, ZeroDivisionError):
            pass
    out = "\n".join(lines) + "\n"
    if advice:
        out += "\n**Diagnosis from your numbers:**\n" + "\n".join(advice) + "\n"
    return out


CHECKLIST = """
- [ ] Reply to every Brief and message within 1 hour (Fiverr app notifications ON)
- [ ] Online during US business hours (18:00-02:00 Pakistan time) - real presence only, never auto-online bots
- [ ] Update `data/manual_stats.csv` with this week's impressions/clicks from the Fiverr dashboard
- [ ] One genuine share of a gig (LinkedIn / X / a Lovable or v0 community) - external clicks are a positive ranking signal
- [ ] Do NOT edit gigs this week unless the report above shows a clear reason (each edit causes a temporary dip)
"""


def main():
    rank_rows = read_csv(DATA / "rank_history.csv")
    health_rows = read_csv(DATA / "gig_health.csv")
    stat_rows = read_csv(DATA / "manual_stats.csv")

    today = date.today().isoformat()
    md = (
        f"# Fiverr Gig Report - {today}\n\n"
        "## 1. Where your gigs rank in Fiverr search\n\n"
        + build_ranking_section(rank_rows)
        + "\n## 2. Gig health\n\n"
        + build_health_section(health_rows)
        + "\n## 3. Your dashboard numbers (manually logged)\n\n"
        + build_manual_stats_section(stat_rows)
        + "\n## 4. This week's checklist\n"
        + CHECKLIST
    )

    (REPORTS / "LATEST.md").write_text(md, encoding="utf-8")
    (REPORTS / f"WEEKLY_REPORT_{today}.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
