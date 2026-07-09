# cyber-news-pipeline

A small automated data pipeline that collects cybersecurity news headlines,
stores them without duplicates, and displays them in a filterable web
dashboard.

Built as Project 11 in a personal cybersecurity / software development
portfolio series.

**Data flow:** `Scrape → Clean → Deduplicate → Store → Display`

<img width="943" height="407" alt="image" src="https://github.com/user-attachments/assets/4f6edcb6-080a-4c8f-9188-f39b3bf66953" />


---

## 1. Scraping ethics — research and decisions

Before writing any code, I looked into what makes web scraping legal and
ethical, and used that to choose the target for this project.

**robots.txt.** This is a file every site can publish at `/robots.txt`
telling automated tools which parts of the site they're allowed to
request. It's not legally binding on its own, but ignoring it is the
first thing that turns "scraping" into "abuse of a service" in most
people's eyes, including a court's if it ever got that far. My scraper
checks robots.txt programmatically before every request (see
`is_allowed_by_robots()` in `scraper.py`) and refuses to continue if
it's disallowed or can't be read.

**Terms of Service.** robots.txt covers *crawlers*; a site's ToS covers
*use of the content*. A site can technically allow crawling but still
prohibit republishing or commercial reuse of what you scrape. Since this
is a personal, non-commercial portfolio project that only stores
headlines, dates, URLs and short summaries (not full article text), and
links back to the original source for anyone who wants to read more,
it stays well inside what's normally considered fair personal/research
use.

**Legal use cases vs. grey areas.** From what I read, scraping is
generally on solid ground when: the data is public, you're not
bypassing a login or paywall, you're not hammering the server (rate
limiting / reasonable request frequency), and you're not reselling or
republishing copyrighted content wholesale. It gets legally risky
when scrapers ignore rate limits, scrape data behind authentication, or
republish full copyrighted articles as if they were the scraper's own
content. This project deliberately avoids all of that.

**Why RSS instead of scraping the rendered HTML site.** RSS feeds are
published by news sites *specifically* so that other tools can pick up
their headlines automatically — that's the entire purpose of the
format. Scraping a feed is a fundamentally lower-risk and more
respectful approach than parsing a site's HTML homepage, because the
site is explicitly offering that data for syndication rather than me
working around a UI meant for humans. I still use `requests` +
`BeautifulSoup` as required by the brief (BeautifulSoup parses the
feed's XML), and I still check robots.txt first — I just chose the
channel a real site would want a bot to use.

**Target:** [The Hacker News](https://thehackernews.com) public RSS
feed. It's a well-known, actively maintained cybersecurity news source,
which fits the project brief directly.

> If you point this at a different site later, re-check that site's
> `robots.txt` and terms of service first — this ethics reasoning is
> specific to the feed used here, not a blanket excuse for scraping
> anything.

---

## 2. Architecture

```
                 ┌─────────────┐
                 │  RSS Feed   │  (thehackernews.com)
                 └──────┬──────┘
                        │ requests.get()
                        ▼
                 ┌─────────────┐
                 │  SCRAPE     │  scraper.py
                 │  BeautifulSoup parses <item> tags:
                 │  headline, date, source, url, summary
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │  CLEAN      │  HTML stripped from summaries,
                 │             │  malformed rows dropped
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │  DEDUPLICATE│  database.py
                 │             │  UNIQUE constraint on url column;
                 │             │  re-inserting a seen URL is a no-op
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │  STORE      │  SQLite (data/articles.db)
                 │             │  + CSV   (data/articles.csv)
                 └──────┬──────┘
                        ▼
                 ┌─────────────┐
                 │  DISPLAY    │  dashboard/app.py (Flask)
                 │             │  filter by keyword / date range
                 └─────────────┘
```

`pipeline.py` runs the Scrape → Clean → Deduplicate → Store steps as one
function, `run_pipeline()`. `scheduler.py` calls that function once
immediately and then every 24 hours using the `schedule` library, so it
can be left running unattended.

---

## 3. Project structure

```
cyber-news-pipeline/
├── config.py                 # feed URL, file paths, constants
├── scraper.py                 # requests + BeautifulSoup, robots.txt check
├── database.py                # SQLite schema, insert/dedupe, CSV export
├── pipeline.py                 # orchestrates one full run
├── scheduler.py                 # runs pipeline every 24h
├── dashboard/
│   ├── app.py                  # Flask app
│   ├── templates/index.html
│   └── static/style.css
├── tests/
│   └── test_pipeline.py         # parsing + dedup tests (no internet needed)
├── data/                        # articles.db / articles.csv / pipeline.log (generated)
├── requirements.txt
└── README.md
```

---

## 4. Setup

```bash
git clone <this-repo>
cd cyber-news-pipeline
python -m venv venv
source venv/bin/activate      # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## 5. Usage

**Run the pipeline once:**
```bash
python pipeline.py
```
This scrapes the feed, cleans and deduplicates the results, and writes
to both `data/articles.db` and `data/articles.csv`. Logs go to both the
console and `data/pipeline.log`.

**Run it automatically every 24 hours:**
```bash
python scheduler.py
```
Runs once immediately, then repeats every 24 hours. Leave the terminal
open (or run it as a background/systemd service) — stop with `Ctrl+C`.

**View the dashboard:**
```bash
python dashboard/app.py
```
Then open `http://127.0.0.1:5000`. The dashboard reads live from
`articles.db`, so re-running the pipeline updates it on next refresh.
Filter by keyword (matches headline or summary) and/or a date range
using the form at the top.

## 6. Testing

```bash
python -m pytest tests/ -v
```

Tests run against a hand-built sample RSS payload and a temporary
SQLite file, so they don't depend on internet access or the live feed
being reachable. They cover:
- correct extraction of headline / date / source / url / summary
- HTML tags being stripped out of summaries
- malformed feed entries being skipped rather than stored as junk
- running the pipeline twice does **not** create duplicate rows
- keyword filtering against stored articles

I also ran the full pipeline manually against sample feed data and
confirmed: first run inserts new rows, second run with identical data
inserts zero new rows (all correctly flagged as duplicates), and the
CSV export matches what's in the database. The dashboard was checked
both unfiltered and with a keyword filter applied, confirming the
filtered view excludes non-matching articles.

## 7. Database schema

```sql
CREATE TABLE articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    headline    TEXT NOT NULL,
    pub_date    TEXT,
    source      TEXT,
    url         TEXT NOT NULL UNIQUE,   -- enforces deduplication
    summary     TEXT,
    scraped_at  TEXT NOT NULL
);
```
