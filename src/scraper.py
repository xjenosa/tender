import os
import re
import logging
import datetime
import threading
from html.parser import HTMLParser

_log = logging.getLogger("tender.scraper")

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")
SAVED_PAGES = ("civd_invitations_page1.html", "civd_invitations_page2.html")
CIVD_DEFAULT_BUYER = "SKK Migas"

def _clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


_MONTHS = {}
for _n, _names in enumerate((
        ("januari", "january", "jan"), ("februari", "february", "feb"), ("maret", "march", "mar"),
        ("april", "apr"), ("mei", "may"), ("juni", "june", "jun"), ("juli", "july", "jul"),
        ("agustus", "august", "agu", "aug", "ags"), ("september", "sept", "sep"),
        ("oktober", "october", "okt", "oct"), ("november", "nov"), ("desember", "december", "des", "dec")),
        start=1):
    for _nm in _names:
        _MONTHS[_nm] = _n


def _valid_iso(y, mo, d):
    try:
        return datetime.date(int(y), int(mo), int(d)).isoformat()
    except ValueError:
        return None


def norm_date(raw):
    s = _clean(raw).casefold()
    if not s:
        return None
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", s)
    if m:
        return _valid_iso(m.group(1), m.group(2), m.group(3))
    m = re.search(r"\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})\b", s)
    if m:
        return _valid_iso(m.group(3), m.group(2), m.group(1))
    m = re.search(r"\b(\d{1,2})[\s\-]+([a-z]{3,})[\s\-,.]*(\d{4})\b", s)
    if m and _MONTHS.get(m.group(2)):
        return _valid_iso(m.group(3), _MONTHS[m.group(2)], m.group(1))
    return None


def _classes(attrs):
    return set((dict(attrs).get("class") or "").split())


class _CivdListingParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards = []
        self.banner = ""
        self._card = None
        self._target = None
        self._field_label = None
        self._field_value = None
        self._in_tipe = False

    def _append(self, key, text):
        self._card[key] = self._card.get(key, "") + text

    def handle_starttag(self, tag, attrs):
        cls = _classes(attrs)
        a = dict(attrs)
        if tag == "div" and "card" in cls:
            self._card = {"fields": {}}
            self.cards.append(self._card)
            return
        if tag == "div" and "pagebanner" in cls:
            self._target = "banner"
            return
        if self._card is None:
            return
        if tag == "h5" and "card-title" in cls:
            self._target = "title"
        elif tag == "small" and "card-subtitle" in cls:
            self._target = "subtitle"
        elif tag == "i" and self._target == "subtitle":
            self._target = "buyer"
        elif tag == "p" and "tipe" in cls:
            self._in_tipe = True
            self._target = None
        elif tag == "p" and "card-text" in cls:
            self._target = "description"
        elif tag == "span" and self._in_tipe:
            self._field_label, self._field_value = "", ""
            self._target = "field_value"
        elif tag == "b" and self._in_tipe and self._field_label is not None:
            self._target = "field_label"
        elif tag == "a" and a.get("data-file-id") and "file_id" not in self._card:
            self._card["file_id"] = a.get("data-file-id")
            self._card["file_name"] = a.get("data-name") or ""

    def handle_endtag(self, tag):
        if self._target == "banner" and tag == "div":
            self._target = None
        elif self._target == "title" and tag == "h5":
            self._target = None
        elif self._target == "buyer" and tag == "i":
            self._target = "subtitle"
        elif self._target == "subtitle" and tag == "small":
            self._target = None
        elif self._target == "field_label" and tag == "b":
            self._target = "field_value"
        elif tag == "span" and self._in_tipe and self._field_label is not None:
            label = _clean(self._field_label).rstrip(":").strip()
            if label:
                self._card["fields"][label] = _clean(self._field_value).lstrip(":").strip()
            self._field_label, self._field_value = None, None
            self._target = None
        elif tag == "p" and self._in_tipe:
            self._in_tipe = False
            self._target = None

    def handle_data(self, data):
        if self._target == "banner":
            self.banner += data
        elif self._target == "field_label":
            self._field_label += data
        elif self._target == "field_value":
            self._field_value += data
        elif self._target in ("title", "subtitle", "buyer", "description") and self._card is not None:
            self._append(self._target, data)
            if self._target == "buyer":
                self._append("subtitle", data)


def _civd_candidate(card):
    title = _clean(card.get("title"))
    if not title:
        return None
    subtitle = _clean(card.get("subtitle"))
    m = re.search(r"Tayang hingga\s+(.+?),", subtitle, re.IGNORECASE)
    fields = card.get("fields") or {}
    description_lines = [f"{k}: {v}" for k, v in fields.items() if v]
    body = _clean(card.get("description"))
    if body and body != title:
        description_lines.insert(0, body)
    return {
        "title": title,
        "tender_ref": card.get("file_id") or "",
        "customer_name": _clean(card.get("buyer")) or CIVD_DEFAULT_BUYER,
        "deadline": norm_date(m.group(1)) if m else None,
        "procurement_type": fields.get("Jenis Pengadaan", ""),
        "description": "\n".join(description_lines),
    }


def parse_civd_listing(html):
    parser = _CivdListingParser()
    parser.feed(html or "")
    parser.close()
    candidates = [c for c in (_civd_candidate(card) for card in parser.cards) if c]
    total = re.search(r"(\d+)\s+items?\s+was found", parser.banner)
    return {"candidates": candidates, "total": int(total.group(1)) if total else len(candidates)}


def read_saved_page(name):
    with open(os.path.join(FIXTURES_DIR, name), encoding="utf-8") as f:
        return f.read()


class CivdAdapter:
    KEY = "civd"

    @classmethod
    def parse(cls, html):
        return parse_civd_listing(html)

    @classmethod
    def fetch(cls, pages=SAVED_PAGES, read=read_saved_page):
        parsed = [cls.parse(read(name)) for name in pages]
        candidates = [c for page in parsed for c in page["candidates"]]
        total = parsed[0]["total"] if parsed else 0
        return {"status": "ok", "candidates": candidates, "total": total,
                "detail": f"{len(candidates)} listings read from {len(parsed)} saved pages"}


ADAPTERS = {
    "civd": CivdAdapter,
}

_ENGINE_LOCK = threading.Lock()


def fetch_all(sources):
    out = {}
    to_read = []
    for s in (sources or []):
        key = ((s.get("key") if isinstance(s, dict) else s) or "").strip().lower()
        if not key or key == "manual":
            continue
        ad = ADAPTERS.get(key)
        if ad is None:
            out[key] = {"status": "no_adapter", "candidates": [], "detail": "no reader for this source"}
        else:
            to_read.append(ad)
    if not to_read:
        return {"busy": False, "sources": out}
    if not _ENGINE_LOCK.acquire(blocking=False):
        return {"busy": True, "sources": {}}
    try:
        for ad in to_read:
            try:
                out[ad.KEY] = ad.fetch()
            except Exception as e:
                _log.exception("scraper %s failed", ad.KEY)
                out[ad.KEY] = {"status": "error", "candidates": [], "detail": str(e)}
        return {"busy": False, "sources": out}
    finally:
        _ENGINE_LOCK.release()
