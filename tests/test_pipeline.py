"""
tests/test_pipeline.py

Lightweight tests that don't require internet access, since they run
against a hand-built sample RSS payload and a temporary SQLite file.
Covers the two things most likely to silently break:
  1. the XML parsing logic in scraper.parse_feed()
  2. the URL-based deduplication logic in database.insert_articles()

Run with:
    python -m pytest tests/ -v
or, without pytest installed:
    python tests/test_pipeline.py
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402
import scraper  # noqa: E402

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Sample Cyber News</title>
  <item>
    <title>Critical Flaw Found in Popular VPN Client</title>
    <link>https://example.com/articles/vpn-flaw</link>
    <pubDate>Mon, 07 Jul 2026 09:00:00 GMT</pubDate>
    <description><![CDATA[<p>Researchers disclosed a <b>remote code execution</b> bug affecting millions of installs.</p>]]></description>
  </item>
  <item>
    <title>New Ransomware Strain Targets Healthcare Sector</title>
    <link>https://example.com/articles/ransomware-healthcare</link>
    <pubDate>Mon, 07 Jul 2026 11:30:00 GMT</pubDate>
    <description>Hospitals in three countries reported outages linked to the malware.</description>
  </item>
  <item>
    <title></title>
    <link></link>
    <pubDate>Mon, 07 Jul 2026 12:00:00 GMT</pubDate>
    <description>This entry is malformed and should be skipped.</description>
  </item>
</channel>
</rss>
"""


class TestScraperParsing(unittest.TestCase):
    def test_parse_feed_extracts_expected_fields(self):
        articles = scraper.parse_feed(SAMPLE_RSS, source_name="Sample Cyber News")
        self.assertEqual(len(articles), 2)  # the malformed 3rd item must be skipped

        first = articles[0]
        self.assertEqual(first["headline"], "Critical Flaw Found in Popular VPN Client")
        self.assertEqual(first["url"], "https://example.com/articles/vpn-flaw")
        self.assertEqual(first["source"], "Sample Cyber News")
        self.assertIn("remote code execution", first["summary"])
        self.assertNotIn("<b>", first["summary"])  # HTML tags stripped

    def test_parse_feed_handles_empty_input(self):
        self.assertEqual(scraper.parse_feed(""), [])


class TestDatabaseDeduplication(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        database.init_db(self.db_path)

    def tearDown(self):
        os.remove(self.db_path)

    def test_duplicate_url_is_skipped_on_second_run(self):
        articles = scraper.parse_feed(SAMPLE_RSS, source_name="Sample Cyber News")

        new1, dup1 = database.insert_articles(articles, self.db_path)
        self.assertEqual(new1, 2)
        self.assertEqual(dup1, 0)

        # Simulate the scraper running again and finding the same articles.
        new2, dup2 = database.insert_articles(articles, self.db_path)
        self.assertEqual(new2, 0)
        self.assertEqual(dup2, 2)

        stored = database.get_all_articles(self.db_path)
        self.assertEqual(len(stored), 2)  # still just 2 rows, not 4

    def test_keyword_filter(self):
        articles = scraper.parse_feed(SAMPLE_RSS, source_name="Sample Cyber News")
        database.insert_articles(articles, self.db_path)

        results = database.get_all_articles(self.db_path, keyword="ransomware")
        self.assertEqual(len(results), 1)
        self.assertIn("Ransomware", results[0]["headline"])


if __name__ == "__main__":
    unittest.main()
