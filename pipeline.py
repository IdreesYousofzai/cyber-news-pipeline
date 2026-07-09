"""
pipeline.py

Ties the whole data flow together:

    Scrape -> Clean -> Deduplicate -> Store -> (Display via dashboard)

Run directly for a single one-off pass:
    python pipeline.py

scheduler.py imports run_pipeline() from here to repeat this every
24 hours without needing its own copy of the logic.
"""

import logging

import config
import database
import scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_PATH),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("pipeline")


def run_pipeline() -> dict:
    """Run one full scrape -> store cycle. Returns a small summary dict."""
    logger.info("Pipeline run starting (source=%s)", config.SOURCE_NAME)

    # 1. SCRAPE - fetch + parse the feed (scraper.py already strips HTML
    #    out of summaries, which doubles as step 2, CLEAN).
    articles = scraper.scrape()
    logger.info("Scraped %d raw articles", len(articles))

    if not articles:
        logger.warning("No articles scraped this run (feed empty, blocked, or unreachable).")
        return {"scraped": 0, "new": 0, "duplicates": 0}

    # 2. CLEAN - drop any rows still missing required fields, just in case.
    cleaned = [
        a for a in articles
        if a.get("headline") and a.get("url")
    ]

    # 3. DEDUPLICATE + 4. STORE - handled together: insert_articles()
    #    relies on the UNIQUE constraint on url in the SQLite schema,
    #    so a duplicate simply isn't inserted a second time.
    database.init_db()
    new_count, dup_count = database.insert_articles(cleaned)

    # Keep the CSV in sync with the database after every run.
    database.export_to_csv()

    summary = {"scraped": len(cleaned), "new": new_count, "duplicates": dup_count}
    logger.info("Pipeline run complete: %s", summary)
    return summary


if __name__ == "__main__":
    run_pipeline()
