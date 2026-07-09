"""
config.py

Central configuration for the cyber-news-pipeline project.
Keeping every path, URL and constant in one place makes the pipeline
easy to point at a different feed later without touching the logic.
"""

import os

# --- Scrape target -----------------------------------------------------
# The Hacker News publishes a public RSS feed intended for syndication.
# Using the feed (rather than scraping the rendered HTML site) is the
# more ethical and more reliable choice for this project - see README.md
# "Scraping Ethics" section for the reasoning.
FEED_URL = "https://feeds.feedburner.com/TheHackersNews"
SOURCE_NAME = "The Hacker News"

# Identify the bot honestly instead of pretending to be a browser.
USER_AGENT = "cyber-news-pipeline/1.0 (+student educational project; contact: idrees-project)"

REQUEST_TIMEOUT = 10  # seconds

# --- Storage -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "articles.db")
CSV_PATH = os.path.join(DATA_DIR, "articles.csv")
LOG_PATH = os.path.join(DATA_DIR, "pipeline.log")

# --- Scheduler -----------------------------------------------------------
RUN_INTERVAL_HOURS = 24

os.makedirs(DATA_DIR, exist_ok=True)
