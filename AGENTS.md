# AGENTS.md

Rules only, read on every prompt, by every member's agent. CLAUDE.md imports
this file rather than copying it, so a rule goes here and only here. What the
project IS lives in README.md.

A Flask app that sorts tender listings from CIVD (SKK Migas) with a keyword
list and an optional language model, and tracks the ones worth bidding on. It
runs on saved CIVD pages, several people work in it, and it is the code behind
a group research project. **This repository is public**, so anything committed
here can be read by anyone, for good.

## The three rules that are not style

### 1. NOTHING PRIVATE GOES IN

- **No labelled answers.** A file that says which listings are relevant, such
  as `evaluation/labels.csv` or a results file with a `label` column, stays on
  your own machine. `.gitignore` already keeps both out. The evaluation runs on
  a labels file you supply.
- **No real company's range.** The keyword list in `src/db.py` and the supplier
  profile in `src/ai_relevance.py` are short generic examples. Put your own in
  your own copy, never in this one.
- **No company, person or price from outside this project,** and nothing pasted
  in from another repository. If something seems to be missing here, it gets
  written here in our own words or it is not needed.
- **Pull request descriptions and comments are public too.** Never quote a
  label, a keyword list or a supplier detail in one.
- **It is checked rather than trusted:** `python tools/no_leak.py` before every
  pull request, and the `no-leak` check runs on every pull request. It refuses
  a labelled answer file, an address of the live CIVD site in the code, an em
  dash, a comment, a committed database or `.env`, and a path out of this
  repository.

### 2. THE APP READS ONLY THE SAVED PAGES

- **The listings come from `fixtures/`:** two CIVD listing pages saved exactly
  as the site returned them. The code holds no address of the live site and
  makes no request to it. ADR 0002.
- **Refresh loads the saved pages,** so a second Refresh finds nothing new.
- **The fixtures are not edited and not added to.** They are saved byte for
  byte. `FIXTURES_SAVED_ON` in `tests/__init__.py` is the day they were saved,
  because closing dates are measured from it.
- **The model step is the one network call.** It goes through OpenRouter with
  the user's own key in `OPENROUTER_API_KEY`, which is never committed.

### 3. THE MODEL PROMOTES AND NEVER HIDES

A keyword match always goes to Bidding and never asks the model. The model only
sees what the keywords missed, and can only move a listing up. A model that is
off, slow, wrong or broken changes nothing. ADR 0003. Any change that lets a
model or a rule hide a listing is a decision, not a fix.

## What must never be committed

- **No secrets and no data.** No `.env`, no API key, nothing from `data/`: the
  database and the log live there and stay local.
- **No generated output**: `venv/`, `__pycache__/`.
- **No private context.** `CLAUDE.local.md`, `QUEUE.md` and
  `.claude/settings.local.json` are where anything you keep to yourself goes.
- **Branch, then open a pull request. Do not push to `main`.**
- **A pull request needs one approval from someone other than its author, and
  the `test` and `no-leak` checks must pass.** Never approve or merge your own;
  ask a teammate to review it. Only Max, as owner, can bypass the approval, and
  only for Max's own pull requests.
- **One pull request does one thing**, so it can be reviewed and reverted on its
  own.
- **Never commit or push unless asked.**
- **Commit subjects are Conventional Commits** (`feat:`, `fix:`, `docs:`,
  `test:`, `chore:`), no body unless it earns its place, no AI co-author
  trailer.
- **A subject that names three things is a commit that should have been three.**

## Conventions

- **No comments and no docstrings in any code file**, `.gitignore` or
  `requirements.txt`. Names carry the meaning; a magic number becomes a named
  constant. ADR 0008. The fixtures are the one exception, because they are
  saved byte for byte.
- No em dash (U+2014) anywhere. A full stop usually does the job.
- Canadian English in anything a person reads.
- **Verify by running the app**, not by the tests alone. `python -m unittest`
  and `python tools/no_leak.py` both pass before a pull request is opened.
- **A check counts once it has been seen to fail.** When you add one, plant the
  defect it is for and watch it go red.
- **When a decision is made, write it down as an ADR in `docs/decisions/`**, as
  it is made. Next number, kebab-case name, and **state the PREMISE inside it**,
  so that when the premise changes there is something to re-read. Add a line to
  `docs/decisions/README.md`. Keep it under a page.
