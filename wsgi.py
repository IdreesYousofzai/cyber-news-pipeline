"""
wsgi.py

Entry point for a WSGI server (PythonAnywhere, gunicorn, etc). It just
exposes the Flask `app` object under the conventional name `application`.

On PythonAnywhere: paste the contents of `pythonanywhere_wsgi_snippet.py`
into the WSGI configuration file the Web tab generates for you (don't
replace the whole file wholesale - see DEPLOY.md for the exact steps).

Running locally, use `python dashboard/app.py` instead - this file is
only needed by the WSGI server itself.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "dashboard"))

from dashboard.app import app as application  # noqa: E402
