import os
import sys
import atexit
import datetime
import logging
import shutil
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "src")
TOOLS = os.path.join(REPO_ROOT, "tools")
FIXTURES = os.path.join(REPO_ROOT, "fixtures")
CIVD_PAGE_1 = os.path.join(FIXTURES, "civd_invitations_page1.html")
CIVD_PAGE_2 = os.path.join(FIXTURES, "civd_invitations_page2.html")
FIXTURES_SAVED_ON = datetime.date(2026, 10, 11)

logging.getLogger("tender.scraper").setLevel(logging.CRITICAL)

for folder in (SRC, TOOLS):
    if folder not in sys.path:
        sys.path.insert(0, folder)

import db

_TMP = tempfile.mkdtemp(prefix="tender_test_")
db.DB_DIR = _TMP
db.DB_PATH = os.path.join(_TMP, "test.db")
db.today = lambda: FIXTURES_SAVED_ON
atexit.register(lambda: shutil.rmtree(_TMP, ignore_errors=True))


def read_fixture(path):
    with open(path, encoding="utf-8") as f:
        return f.read()
