"""
scheduler.py

Runs the pipeline once immediately, then automatically every 24 hours,
using the `schedule` library. Leave this running in a terminal (or as
a background service / cron-launched process) and it takes care of
re-scraping without any manual triggering.

Usage:
    python scheduler.py

Stop with Ctrl+C.
"""

import logging
import time

import schedule

import config
from pipeline import run_pipeline

logger = logging.getLogger("scheduler")


def job():
    try:
        run_pipeline()
    except Exception:  # noqa: BLE001 - a bad run should not kill the scheduler
        logger.exception("Scheduled pipeline run failed")


def main():
    logging.basicConfig(level=logging.INFO)
    logger.info(
        "Starting scheduler: running now, then every %d hours.",
        config.RUN_INTERVAL_HOURS,
    )

    job()  # run once immediately so you don't wait a full day for the first data
    schedule.every(config.RUN_INTERVAL_HOURS).hours.do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)  # check once a minute; the actual job only fires every 24h


if __name__ == "__main__":
    main()
