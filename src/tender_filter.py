import re
import hashlib

STOPWORDS = {
    "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "with", "by", "from", "at",
    "as", "is", "are", "be", "new", "used", "type", "types", "model", "unit", "units", "set",
    "sets", "pcs", "piece", "pieces", "item", "items", "qty", "quantity", "package", "packages",
    "project", "projects", "tender", "rfq", "rfp", "supply", "supplies", "provision", "purchase",
    "procurement", "service", "services", "work", "works", "spec", "specs", "specification",
    "including", "include", "various", "general", "requirement", "requirements",
    "pengadaan", "jasa", "pekerjaan", "paket", "untuk", "dan", "atau", "di", "ke", "dari",
    "dengan", "yang", "pada", "adalah", "buah", "barang", "penyediaan", "pembelian",
    "pengiriman", "pemeliharaan", "perbaikan", "sewa", "spesifikasi", "tipe", "serta", "guna",
    "keperluan", "kebutuhan", "sesuai", "beserta",
}

FIELD_SEPARATOR = chr(0x241F)
MIN_TOKEN_LENGTH = 3
_TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)


def _norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().casefold()


def _term_pattern(term):
    parts = [re.escape(p) for p in _norm(term).split(" ") if p]
    if not parts:
        return None
    body = r"\s+".join(parts)
    return re.compile(r"(?<!\w)" + body + r"(?!\w)", re.IGNORECASE | re.UNICODE)


def _matches(haystack, terms):
    hay = _norm(haystack)
    hits, seen = [], set()
    for t in terms:
        key = _norm(t)
        if not key or key in seen:
            continue
        seen.add(key)
        pat = _term_pattern(t)
        if pat and pat.search(hay):
            hits.append(t)
    return hits


def content_fingerprint(*parts):
    joined = FIELD_SEPARATOR.join(_norm(p) for p in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def term_key(term):
    return _norm(term)


def keyword_gate(haystack, include_terms):
    terms = [t for t in (include_terms or []) if str(t).strip()]
    if not terms:
        return True, {"matched_include": [], "filter_off": True}
    inc = _matches(haystack, terms)
    return bool(inc), {"matched_include": inc, "filter_off": False}


def gate_reason(info):
    if info.get("filter_off"):
        return "filter off (no inclusion keywords): showing all"
    if info.get("matched_include"):
        return "matched: " + ", ".join(info["matched_include"])
    return "no inclusion keyword matched"


def _share(part, whole):
    return part / whole if whole else None


def gate_scores(labelled, include_terms):
    caught, missed, let_through, held_back = [], [], [], []
    by_term = {}
    for title, relevant in labelled:
        passed, info = keyword_gate(title, include_terms)
        if passed and relevant:
            caught.append(title)
        elif passed:
            let_through.append(title)
        elif relevant:
            missed.append(title)
        else:
            held_back.append(title)
        for term in info["matched_include"]:
            counts = by_term.setdefault(term, {"caught": 0, "let_through": 0})
            counts["caught" if relevant else "let_through"] += 1
    return {
        "recall": _share(len(caught), len(caught) + len(missed)),
        "precision": _share(len(caught), len(caught) + len(let_through)),
        "caught": caught,
        "missed": missed,
        "let_through": let_through,
        "held_back": held_back,
        "by_term": by_term,
    }


def loose_terms(by_term):
    loose = [t for t, c in by_term.items() if c["let_through"] > c["caught"]]
    return sorted(loose, key=lambda t: (-by_term[t]["let_through"], t))


def tokens(title):
    return [w for w in _TOKEN.findall(_norm(title)) if len(w) >= MIN_TOKEN_LENGTH and w not in STOPWORDS]


def relevance_check(haystack, include_terms, mode="off", profile=None, judge=None):
    passed, info = keyword_gate(haystack, include_terms)
    if passed or mode not in ("ollama", "api") or judge is None:
        return passed, gate_reason(info)
    try:
        relevant, why = judge(haystack, profile)
    except Exception:
        return passed, gate_reason(info)
    if relevant:
        return True, "AI: " + ((why or "").strip() or "a supplied item")
    return passed, gate_reason(info)
