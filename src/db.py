import os
import json
import sqlite3
import datetime
import secrets

import tender_filter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def database_path(env):
    chosen = (env.get("TENDER_DB") or "").strip()
    return os.path.abspath(chosen) if chosen else os.path.join(REPO_ROOT, "data", "tender.db")


DB_PATH = database_path(os.environ)
DB_DIR = os.path.dirname(DB_PATH)

PURGE_AFTER_DAYS = 60
REVISION_QUIET_MINUTES = 10
CLOSED_HIDE_AFTER_DAYS = 30
CLOSED_ON_SQL = "date(COALESCE(date_submission, last_seen, created_at))"
KEYWORD_COOLDOWN_BUSINESS_DAYS = 5
LEARN_CAP_PER_TITLE = 6
PAGES_SAVED_ON = datetime.date(2026, 10, 11)
MANUAL_SOURCE = {"key": "manual", "label": "Manual", "color": "#8e24aa"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS tenders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT,
    title TEXT,
    customer_name TEXT,
    description TEXT,
    source TEXT DEFAULT 'manual',
    tender_ref TEXT,
    stage TEXT DEFAULT 'spotted',
    date_registration TEXT,
    date_prebid TEXT,
    date_clarification TEXT,
    date_submission TEXT,
    date_delivery TEXT,
    date_invoice TEXT,
    date_payment TEXT,
    contract_value REAL,
    payment_status TEXT,
    lost_reason TEXT,
    winner_price REAL,
    pic TEXT,
    notes TEXT,
    next_action TEXT,
    dismissed_at TEXT,
    bucketed_at TEXT,
    fingerprint TEXT,
    matched INTEGER DEFAULT 0,
    last_seen TEXT,
    last_changed TEXT,
    not_relevant_at TEXT,
    prev_snapshot TEXT,
    sort_order INTEGER,
    model_reason TEXT
);
CREATE TABLE IF NOT EXISTS tender_keyword (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    term TEXT NOT NULL,
    term_norm TEXT NOT NULL UNIQUE,
    origin TEXT NOT NULL DEFAULT 'manual',
    active INTEGER NOT NULL DEFAULT 1,
    added_at TEXT DEFAULT (datetime('now','localtime')),
    removed_at TEXT,
    cooldown_until TEXT
);
"""

DEFAULT_INCLUDE_TERMS = [
    "pump", "pompa", "compressor", "kompresor", "turbine", "generator", "engine", "bearing",
    "spare parts", "suku cadang",
]

DEFAULT_SETTINGS = {
    "tender_sources": json.dumps([
        {"key": "civd", "label": "CIVD SKK Migas", "color": "#7cb342"},
        MANUAL_SOURCE,
    ]),
    "tender_relevance_mode": "off",
    "tender_relevance_model": "",
    "tender_relevance_endpoint": "",
}


def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    for k, v in DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?,?)", (k, v))
    for term in DEFAULT_INCLUDE_TERMS:
        conn.execute("INSERT OR IGNORE INTO tender_keyword(term, term_norm, origin) VALUES (?,?,'manual')",
                     (term, tender_filter.term_key(term)))
    conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?,?)",
                 ("secret_key", secrets.token_hex(32)))
    conn.commit()
    conn.close()


def get_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def save_settings(values):
    conn = get_db()
    for k, v in values.items():
        conn.execute("INSERT INTO settings(key,value) VALUES (?,?) "
                     "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, str(v)))
    conn.commit()
    conn.close()


def today():
    return PAGES_SAVED_ON


def days_before_today(days):
    return (today() - datetime.timedelta(days=days)).isoformat()


def sweep_tenders():
    conn = get_db()
    conn.execute("UPDATE tenders SET bucketed_at=datetime('now','localtime') "
                 "WHERE dismissed_at IS NOT NULL AND bucketed_at IS NULL "
                 "AND date(dismissed_at) < date('now','localtime')")
    purge_cutoff = f"-{PURGE_AFTER_DAYS} days"
    conn.execute("DELETE FROM tenders WHERE bucketed_at IS NOT NULL "
                 "AND date(bucketed_at) < date('now','localtime',?)", (purge_cutoff,))
    conn.execute("DELETE FROM tenders WHERE stage='feed' AND not_relevant_at IS NOT NULL "
                 "AND date(not_relevant_at) < date('now','localtime',?)", (purge_cutoff,))
    conn.execute(f"DELETE FROM tenders WHERE stage='feed' AND {CLOSED_ON_SQL} < ?",
                 (days_before_today(PURGE_AFTER_DAYS),))
    conn.commit()
    conn.close()


def _json_setting(key, fallback):
    raw = get_settings().get(key)
    if raw is None:
        raw = DEFAULT_SETTINGS.get(key)
    try:
        v = json.loads(raw) if raw else None
    except (ValueError, TypeError):
        v = None
    return v if v is not None else fallback


def tender_sources_list():
    out, seen = [], set()
    for r in _json_setting("tender_sources", []):
        k = (r.get("key") or "").strip()
        if k and k not in seen:
            seen.add(k)
            out.append({"key": k, "label": r.get("label") or k, "color": r.get("color") or MANUAL_SOURCE["color"]})
    if MANUAL_SOURCE["key"] not in seen:
        out.append(dict(MANUAL_SOURCE))
    return out


def source_map():
    return {s["key"]: {"label": s["label"], "color": s["color"]} for s in tender_sources_list()}


def tender_source_tuples():
    return [(s["key"], s["label"], s["color"]) for s in tender_sources_list()]


def tender_include_terms():
    conn = get_db()
    rows = conn.execute("SELECT term FROM tender_keyword WHERE COALESCE(active,1)=1 "
                        "ORDER BY term COLLATE NOCASE").fetchall()
    conn.close()
    return [r["term"].strip() for r in rows if (r["term"] or "").strip()]


def _business_days_after(start_date, n):
    d, left = start_date, n
    while left > 0:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            left -= 1
    return d


def tender_keywords(active_only=True):
    conn = get_db()
    q = ("SELECT id, term, origin, COALESCE(active,1) AS active, added_at, cooldown_until "
         "FROM tender_keyword ")
    if active_only:
        q += "WHERE COALESCE(active,1)=1 "
    q += "ORDER BY term COLLATE NOCASE"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_tender_keyword(term, origin="manual"):
    term = (term or "").strip()
    if not term:
        return False
    norm = tender_filter.term_key(term)
    if not norm:
        return False
    conn = get_db()
    row = conn.execute("SELECT id, COALESCE(active,1) AS active, cooldown_until FROM tender_keyword "
                       "WHERE term_norm=?", (norm,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO tender_keyword(term, term_norm, origin, active, added_at) "
                     "VALUES (?,?,?,1, datetime('now','localtime'))", (term, norm, origin))
        conn.commit()
        conn.close()
        return True
    if row["active"]:
        conn.close()
        return False
    if origin == "learned" and row["cooldown_until"]:
        blocked = conn.execute("SELECT date(?) >= date('now','localtime') AS b",
                               (row["cooldown_until"],)).fetchone()["b"]
        if blocked:
            conn.close()
            return False
    conn.execute("UPDATE tender_keyword SET term=?, active=1, origin=?, added_at=datetime('now','localtime'), "
                 "removed_at=NULL, cooldown_until=NULL WHERE id=?", (term, origin, row["id"]))
    conn.commit()
    conn.close()
    return True


def remove_tender_keyword(term):
    norm = tender_filter.term_key(term)
    if not norm:
        return
    cooldown = _business_days_after(datetime.date.today(), KEYWORD_COOLDOWN_BUSINESS_DAYS).isoformat()
    conn = get_db()
    conn.execute("UPDATE tender_keyword SET active=0, removed_at=datetime('now','localtime'), "
                 "cooldown_until=? WHERE term_norm=?", (cooldown, norm))
    conn.commit()
    conn.close()


def learn_keywords_from_title(title, cap=LEARN_CAP_PER_TITLE):
    added = []
    for tok in tender_filter.tokens(title or ""):
        if len(added) >= cap:
            break
        if add_tender_keyword(tok, origin="learned"):
            added.append(tok)
    return added


def _revised_listing(conn, source, title, cust, ref):
    rows = conn.execute(
        "SELECT * FROM tenders WHERE source=? AND title=? AND COALESCE(customer_name,'')=? "
        "AND COALESCE(tender_ref,'')<>'' AND tender_ref<>? "
        "AND (last_seen IS NULL OR last_seen < datetime('now','localtime',?))",
        (source, title, cust or "", ref, f"-{REVISION_QUIET_MINUTES} minutes")).fetchall()
    return rows[0] if len(rows) == 1 else None


def ingest_tender(source, title, tender_ref=None, customer_name=None, deadline=None,
                  matched=False, description=None, model_reason=None):
    title = (title or "").strip()
    if not title:
        return "dropped"
    ref = (tender_ref or "").strip()
    cust = (customer_name or "").strip() or None
    dl = (deadline or "").strip() or None
    desc = (description or "").strip() or None
    why = (model_reason or "").strip() or None
    fp = tender_filter.content_fingerprint(title, cust or "", ref, dl or "")
    conn = get_db()
    if ref:
        row = conn.execute("SELECT * FROM tenders WHERE source=? AND tender_ref=? LIMIT 1",
                           (source, ref)).fetchone()
        if row is None:
            row = _revised_listing(conn, source, title, cust, ref)
            if row is not None:
                conn.execute("UPDATE tenders SET tender_ref=? WHERE id=?", (ref, row["id"]))
    else:
        row = conn.execute("SELECT * FROM tenders WHERE source=? AND title=? AND "
                           "(tender_ref IS NULL OR tender_ref='') LIMIT 1", (source, title)).fetchone()
    if row is None:
        stage = "spotted" if matched else "feed"
        conn.execute(
            "INSERT INTO tenders(title, customer_name, description, source, tender_ref, date_submission, stage, "
            "matched, model_reason, fingerprint, last_seen, sort_order) VALUES (?,?,?,?,?,?,?,?,?,?, "
            "datetime('now','localtime'), (SELECT COALESCE(MAX(sort_order),0)+1 FROM tenders))",
            (title, cust, desc, source, ref or None, dl, stage, 1 if matched else 0, why if matched else None, fp))
        conn.commit()
        conn.close()
        return "new"
    changed = row["fingerprint"] != fp
    promote = bool(matched and row["stage"] == "feed" and not row["dismissed_at"])
    sets, vals = ["last_seen=datetime('now','localtime')", "description=COALESCE(?, description)"], [desc]
    if promote:
        sets += ["stage='spotted'", "matched=1", "model_reason=?"]
        vals.append(why)
    if changed:
        prev = json.dumps({"title": row["title"], "customer_name": row["customer_name"],
                           "tender_ref": row["tender_ref"], "date_submission": row["date_submission"]})
        sets += ["title=?", "customer_name=COALESCE(?, customer_name)",
                 "date_submission=COALESCE(?, date_submission)", "fingerprint=?", "prev_snapshot=?",
                 "last_changed=datetime('now','localtime')", "not_relevant_at=NULL"]
        vals += [title, cust, dl, fp, prev]
    conn.execute(f"UPDATE tenders SET {', '.join(sets)} WHERE id=?", (*vals, row["id"]))
    conn.commit()
    conn.close()
    return "updated" if changed else ("promoted" if promote else "unchanged")


if __name__ == "__main__":
    init_db()
    print("Database ready at", DB_PATH)
