import os
import re
import io
import ast
import csv
import sys
import tokenize
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINARY = re.compile(r"\.(png|jpe?g|gif|webp|ico|pdf|woff2?|ttf|otf|zip|db|sqlite3?)$", re.IGNORECASE)
SKIP_DIRS = {".git", "data", "venv", ".venv", "__pycache__", "node_modules", ".claude"}
CODE_DIRS = ("src/", "tests/", "tools/")
LIVE_CODE_DIRS = ("src/", "tools/")
EM_DASH = chr(0x2014)
LOCAL_PATH = re.compile(r"\b[A-Za-z]:[\\/]+Users\b|/[a-z]/Users/|AppData[\\/]", re.IGNORECASE)
JS_LINE_COMMENT = re.compile(r"(^|[\s;{}(),])//")
PRIVATE_FILE = re.compile(r"(^|/)(data/|\.env($|\.)(?!example))|\.(db|sqlite3?)$")
LIVE_SITE = re.compile(r"skkmigas\.go\.id", re.IGNORECASE)
ANSWER_FILE = "evaluation/labels.csv"
ANSWER_COLUMN = "label"


def repo_files():
    try:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                             cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
        files = [f for f in out.splitlines() if f]
    except (OSError, subprocess.CalledProcessError):
        files = []
        for root, dirs, names in os.walk(REPO_ROOT):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in names:
                files.append(os.path.relpath(os.path.join(root, name), REPO_ROOT).replace(os.sep, "/"))
    return sorted(f for f in files if os.path.isfile(os.path.join(REPO_ROOT, f)))


def read(path):
    with open(os.path.join(REPO_ROOT, path), encoding="utf-8", errors="replace") as f:
        return f.read()


def line_of(text, index):
    return text.count("\n", 0, index) + 1


def csv_columns(path):
    first = read(path).splitlines()[:1]
    if not first:
        return []
    return [c.strip().lower() for c in next(csv.reader(first))]


def check_answers(files):
    return [f for f in files
            if f == ANSWER_FILE or (f.lower().endswith(".csv") and ANSWER_COLUMN in csv_columns(f))]


def check_live_site(files):
    rows = []
    for f in files:
        if not f.startswith(LIVE_CODE_DIRS):
            continue
        text = read(f)
        m = LIVE_SITE.search(text)
        if m:
            rows.append(f"{f}:{line_of(text, m.start())}")
    return rows


def check_em_dash(files):
    rows = []
    for f in files:
        text = read(f)
        i = text.find(EM_DASH)
        if i != -1:
            rows.append(f"{f}:{line_of(text, i)}")
    return rows


def python_comments(path, text):
    rows = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
        tree = ast.parse(text)
    except (SyntaxError, tokenize.TokenError) as e:
        return [f"{path}:{getattr(e, 'lineno', 1) or 1}  does not parse, so it cannot be checked"]
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            rows.append(f"{path}:{tok.start[0]}  comment")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if ast.get_docstring(node, clean=False) is not None:
                rows.append(f"{path}:{getattr(node, 'lineno', 1)}  docstring")
    return rows


def markup_comments(path, text):
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        if path.endswith((".js", ".css", ".html")) and "/*" in line:
            rows.append(f"{path}:{n}  block comment")
        if path.endswith((".js", ".html")) and JS_LINE_COMMENT.search(line):
            rows.append(f"{path}:{n}  line comment")
        if path.endswith(".html") and ("<!--" in line or "{#" in line):
            rows.append(f"{path}:{n}  markup comment")
    return rows


def check_comments(files):
    rows = []
    for f in files:
        if not f.startswith(CODE_DIRS):
            continue
        text = read(f)
        if f.endswith(".py"):
            rows += python_comments(f, text)
        elif f.endswith((".js", ".css", ".html")):
            rows += markup_comments(f, text)
    for f in (".gitignore", "requirements.txt"):
        if f in files and any(line.lstrip().startswith("#") for line in read(f).splitlines()):
            rows.append(f"{f}  comment")
    return rows


def check_private_files(files):
    return [f for f in files if PRIVATE_FILE.search(f)]


def check_local_paths(files):
    rows = []
    for f in files:
        text = read(f)
        m = LOCAL_PATH.search(text)
        if m:
            rows.append(f"{f}:{line_of(text, m.start())}")
    return rows


CHECKS = [
    ("no-answers", "no file of labelled listings is in the repository", check_answers),
    ("no-live-site", "the code holds no address of the live CIVD site", check_live_site),
    ("no-em-dash", "no em dash in any file", check_em_dash),
    ("no-comments", "no comment or docstring in code, .gitignore or requirements.txt", check_comments),
    ("no-private-files", "no database, data folder or .env is in the repository", check_private_files),
    ("no-local-paths", "no path out of this repository", check_local_paths),
]


def main():
    files = [f for f in repo_files() if not BINARY.search(f)]
    failed = 0
    for check_id, rule, check in CHECKS:
        rows = check(files)
        print(("ok    " if not rows else "FAIL  ") + check_id + ": " + rule)
        for row in rows:
            print("        " + row)
        failed += bool(rows)
    print(f"\n{len(CHECKS) - failed} of {len(CHECKS)} checks passed over {len(files)} files")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
