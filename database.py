"""
database.py

SQLite storage layer for scraped articles. The URL column is UNIQUE,
which is what actually enforces deduplication: re-running the scraper
on the same feed will try to insert the same URL again, and SQLite
will reject it. insert_article() treats that rejection as "already
have it" rather than an error.
"""

import csv
import logging
import os
import sqlite3
from datetime import datetime, timezone

import config

logger = logging.getLogger("database")

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    headline    TEXT NOT NULL,
    pub_date    TEXT,
    source      TEXT,
    url         TEXT NOT NULL UNIQUE,
    summary     TEXT,
    scraped_at  TEXT NOT NULL
);
"""


def get_connection(db_path: str = config.DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = config.DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.execute(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_article(article: dict, db_path: str = config.DB_PATH) -> bool:
    """Insert one article. Returns True if it was newly added,
    False if it was a duplicate (already present by URL)."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO articles (headline, pub_date, source, url, summary, scraped_at)
            VALUES (:headline, :date, :source, :url, :summary, :scraped_at)
            """,
            {**article, "scraped_at": datetime.now(timezone.utc).isoformat()},
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # UNIQUE constraint on url -> duplicate, safe to ignore.
        return False
    finally:
        conn.close()


def insert_articles(articles: list[dict], db_path: str = config.DB_PATH) -> tuple[int, int]:
    """Insert many articles, returns (new_count, duplicate_count)."""
    new_count = 0
    dup_count = 0
    for article in articles:
        if insert_article(article, db_path):
            new_count += 1
        else:
            dup_count += 1
    logger.info("Insert complete: %d new, %d duplicates skipped", new_count, dup_count)
    return new_count, dup_count


def get_all_articles(
    db_path: str = config.DB_PATH,
    keyword: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Return articles, most recently scraped first, with optional filters.

    keyword    - case-insensitive match against headline or summary
    start_date - ISO date string (YYYY-MM-DD), filters on scraped_at
    end_date   - ISO date string (YYYY-MM-DD), filters on scraped_at
    """
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM articles WHERE 1=1"
        params: list = []

        if keyword:
            query += " AND (headline LIKE ? OR summary LIKE ?)"
            like_term = f"%{keyword}%"
            params.extend([like_term, like_term])

        if start_date:
            query += " AND date(scraped_at) >= date(?)"
            params.append(start_date)

        if end_date:
            query += " AND date(scraped_at) <= date(?)"
            params.append(end_date)

        query += " ORDER BY scraped_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def export_to_csv(csv_path: str = config.CSV_PATH, db_path: str = config.DB_PATH) -> None:
    """Dump the full articles table to CSV, overwriting any existing file."""
    articles = get_all_articles(db_path)
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    fieldnames = ["id", "headline", "pub_date", "source", "url", "summary", "scraped_at"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in articles:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    logger.info("Exported %d articles to %s", len(articles), csv_path)
