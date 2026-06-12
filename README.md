# Fiverr Gig Booster

Automation that watches your Fiverr gigs from GitHub and keeps you on the
habits that actually rank gigs. Pre-configured for **anas_982** - deploy as-is,
no code changes required.

## What it does (automatically)

| Workflow | When | What you get |
|---|---|---|
| **Daily Rank Tracker** | every day, 09:30 PKT | Records on which Fiverr search page/position your gigs appear for each keyword in `config.json`, plus DuckDuckGo/Google visibility. Saved to `data/rank_history.csv`. Also checks each gig is still live (early warning if Fiverr pauses/flags a gig). |
| **Daily Online Reminder** | every day, 18:00 PKT | Opens a GitHub Issue with a prime-time checklist (go online, answer Briefs, etc.). GitHub emails it to you - that email is your reminder. Yesterday's issue auto-closes. |
| **Weekly Gig Report** | Sunday, 10:00 PKT | A Markdown report: keyword ranking trends vs last week, gig health, CTR diagnosis from your dashboard numbers, and a checklist. Posted as an issue (= emailed to you). |

## What it deliberately does NOT do (read this)

- There is **no official Fiverr seller API**, so nothing can directly change
  your ranking. Ranking comes from clicks, orders, reviews and your Success
  Score. This repo measures and reminds; *you* convert.
- It **never logs into Fiverr** and **never fakes online status**. Auto-online
  bots violate Fiverr's Terms of Service and get accounts banned. Go online
  for real, from the Fiverr app, when the reminder arrives.
- Fiverr sometimes blocks datacenter IPs (like GitHub's). On those days rank
  rows say `BLOCKED` instead of failing - the tracker just retries the next
  day, and DuckDuckGo visibility usually still works.

## Deploy in 3 steps (about 3 minutes)

**Step 1 - Create the repo.** Go to <https://github.com/new>, name it
`fiverr-gig-booster`, choose **Public** (public repos get unlimited free
Actions minutes), click **Create repository**.

**Step 2 - Upload these files.** On the new empty repo page click
**"uploading an existing file"**. Unzip this folder on your computer, open it,
select **everything inside it** (including the `.github` folder) and drag it
into the browser. Click **Commit changes**.
> If the `.github` folder doesn't upload by drag-and-drop in your browser,
> use git instead:
> ```bash
> cd fiverr-gig-booster
> git init && git add . && git commit -m "init"
> git branch -M main
> git remote add origin https://github.com/YOUR_USERNAME/fiverr-gig-booster.git
> git push -u origin main
> ```

**Step 3 - Allow Actions to write.** In the repo: **Settings -> Actions ->
General -> Workflow permissions -> select "Read and write permissions" ->
Save.** Then open the **Actions** tab, enable workflows if asked, click each
workflow and press **Run workflow** once to test.

That's it. Check **Issues** - the reminder appears there daily, and GitHub
emails it to you (Settings -> Notifications must allow email for
"Participating, @mentions and custom" / watched repos - it's on by default
for your own repos).

## Your one weekly job

Fiverr does not show impressions publicly, so once a week copy them from
**Fiverr -> Gigs** into `data/manual_stats.csv` (one row per gig). The weekly
report then diagnoses your funnel automatically:

- 0 impressions  -> visibility problem (keywords/tags/gig status)
- impressions but CTR < 1.5% -> thumbnail / title / starting price problem
- clicks but no messages -> description / proof / trust problem

## Customizing (optional)

- **Keywords**: edit `config.json` (these are what the tracker searches for).
- **Times**: edit the `cron:` lines in `.github/workflows/*.yml` (UTC; PKT = UTC+5).
- **Gigs**: add/remove entries in `config.json` - `name` is just a short label.

## Files

```
config.json                      <- your gigs + keywords (pre-filled)
.github/workflows/               <- the 3 automations
scripts/                         <- Python that does the work
data/rank_history.csv            <- grows daily (committed by the bot)
data/gig_health.csv              <- grows daily
data/manual_stats.csv            <- YOU update weekly from Fiverr dashboard
reports/                         <- weekly Markdown reports
docs/GIG_OPTIMIZATION_GUIDE.md   <- the full optimization plan for your 3 gigs
```

## Troubleshooting

- **Workflows didn't run on schedule** - GitHub can delay cron jobs up to ~1
  hour; also, schedules pause if a repo has no activity for 60 days (the daily
  data commits prevent that). First run should always be manual.
- **"Permission denied" on git push in the log** - you skipped Step 3
  (Workflow permissions -> Read and write).
- **All rank rows say BLOCKED** - Fiverr blocked GitHub's IP that day. Normal.
  It retries tomorrow; the reminder and report workflows are unaffected.
