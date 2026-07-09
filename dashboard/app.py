"""
dashboard/app.py

Small Flask app that reads articles straight out of the SQLite database
(no separate export step needed) and renders them in a filterable table.

Run with:
    python dashboard/app.py

Then open http://127.0.0.1:5000
"""

import os
import subprocess
import sys

from flask import Flask, jsonify, render_template, request

# Allow "import database" / "import config" from the project root when this
# file is run directly from inside dashboard/.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import config  # noqa: E402
import database  # noqa: E402

app = Flask(__name__)

# Used by the /sync route below. Set this as a real secret once deployed:
# on PythonAnywhere, Web tab -> Environment variables -> SYNC_TOKEN.
# Falls back to a placeholder locally so the route still works for testing.
SYNC_TOKEN = os.environ.get("SYNC_TOKEN", "change-me-before-deploying")


@app.route("/")
def index():
    keyword = request.args.get("keyword", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    database.init_db()  # harmless if it already exists; keeps a fresh clone working
    articles = database.get_all_articles(
        keyword=keyword or None,
        start_date=start_date or None,
        end_date=end_date or None,
    )

    all_articles = database.get_all_articles()
    last_sync = all_articles[0]["scraped_at"] if all_articles else None

    return render_template(
        "index.html",
        articles=articles,
        total_count=len(all_articles),
        shown_count=len(articles),
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        last_sync=last_sync,
        source_name=config.SOURCE_NAME,
    )


@app.route("/sync")
def sync():
    """Pull the latest commit (which GitHub Actions pushes after each
    scrape) so the deployed dashboard picks up fresh data without a
    manual redeploy. Protected by a shared token so randoms can't spam
    git pulls on your server.
    """
    token = request.args.get("token", "")
    if token != SYNC_TOKEN:
        return jsonify({"ok": False, "error": "invalid token"}), 403

    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return jsonify(
            {
                "ok": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500


if __name__ == "__main__":
    database.init_db()
    # debug=True is for local development only. When this is deployed
    # (e.g. behind PythonAnywhere's WSGI server, or gunicorn elsewhere),
    # this __main__ block never runs, so debug mode is never exposed
    # publicly.
    app.run(debug=True)
