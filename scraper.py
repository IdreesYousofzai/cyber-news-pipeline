"""
scraper.py

Fetches cybersecurity news headlines from a public RSS feed and parses
them with requests + BeautifulSoup, as required by the project brief.

An RSS feed is used rather than scraping the rendered HTML homepage.
Feeds are published by sites specifically so that content can be picked
up by third-party tools; that makes this a low-risk, clearly-permitted
form of "scraping" compared to pulling full article text out of HTML
that was designed for humans reading it in a browser. See README.md for
the full ethics writeup.

Even though a feed is being used, this module still:
  - checks robots.txt before making a request,
  - identifies itself with a real User-Agent,
  - fails safely and logs a clear reason if the feed is unreachable.
"""

import logging
import urllib.robotparser
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger("scraper")


def is_allowed_by_robots(url: str, user_agent: str) -> bool:
    """Check robots.txt for the target domain before requesting anything.

    Fails "closed" on network errors involving robots.txt itself: if we
    can't retrieve robots.txt at all, we don't assume permission - we
    only proceed if it's fetched and explicitly allows us.
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception as exc:  # noqa: BLE001 - we want to log and continue safely
        logger.warning("Could not read %s (%s). Skipping run to be safe.", robots_url, exc)
        return False

    allowed = rp.can_fetch(user_agent, url)
    if not allowed:
        logger.warning("robots.txt at %s disallows fetching %s", robots_url, url)
    return allowed


def fetch_raw_feed(feed_url: str = config.FEED_URL) -> str:
    """Download the raw RSS/XML content of the feed."""
    headers = {"User-Agent": config.USER_AGENT}
    response = requests.get(feed_url, headers=headers, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def _clean_html(raw_html: str) -> str:
    """Strip HTML tags out of an RSS <description> and collapse whitespace."""
    if not raw_html:
        return ""
    text = BeautifulSoup(raw_html, "html.parser").get_text(separator=" ")
    return " ".join(text.split())


def parse_feed(xml_content: str, source_name: str = config.SOURCE_NAME) -> list[dict]:
    """Parse RSS XML into a list of article dicts.

    Each dict has: headline, date, source, url, summary.
    """
    soup = BeautifulSoup(xml_content, "xml")
    items = soup.find_all("item")

    articles = []
    for item in items:
        title_tag = item.find("title")
        link_tag = item.find("link")
        date_tag = item.find("pubDate")
        desc_tag = item.find("description")

        headline = title_tag.get_text(strip=True) if title_tag else ""
        url = link_tag.get_text(strip=True) if link_tag else ""
        pub_date = date_tag.get_text(strip=True) if date_tag else ""
        summary = _clean_html(desc_tag.get_text() if desc_tag else "")

        # Trim overly long summaries down to something dashboard-friendly.
        if len(summary) > 400:
            summary = summary[:397].rstrip() + "..."

        if not headline or not url:
            # Skip malformed entries rather than storing junk rows.
            continue

        articles.append(
            {
                "headline": headline,
                "date": pub_date,
                "source": source_name,
                "url": url,
                "summary": summary,
            }
        )

    return articles


def scrape(feed_url: str = config.FEED_URL, source_name: str = config.SOURCE_NAME) -> list[dict]:
    """High-level entry point: check robots.txt, fetch, parse, return articles."""
    if not is_allowed_by_robots(feed_url, config.USER_AGENT):
        logger.error("Aborting scrape: robots.txt does not permit fetching %s", feed_url)
        return []

    try:
        raw = fetch_raw_feed(feed_url)
    except requests.RequestException as exc:
        logger.error("Failed to fetch feed %s: %s", feed_url, exc)
        return []

    return parse_feed(raw, source_name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    found = scrape()
    print(f"Parsed {len(found)} articles")
    for a in found[:5]:
        print(a["date"], "-", a["headline"])
