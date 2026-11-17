# 0019. Dates run from the day the pages were saved

Status: Accepted, 2026-11-14. Track C. Follows ADR 0002.

## Context

**This copy reads two CIVD pages saved on 11 October 2026 (ADR 0002), and they
never change.** Counted from the real date, every listing closes further in the
past each day: All Tenders hides it after 30 days (ADR 0010) and the app deletes
it after 60, so the app would empty out a few weeks after the pages were saved.

## Decision

**`db.today()` is 11 October 2026, the day the pages were saved.** Closing
dates, the 30 and 60 day windows, the reminders and the calendar all count from
it, so the app shows the same listings whenever it runs.

- **Only the listings' dates.** When a card was added, changed or dismissed
  stays the real time, and so does a removed keyword's five-day wait.

**PREMISE:** the saved pages never change. If this copy ever reads newer pages,
`PAGES_SAVED_ON` moves with them, or this is re-read.

## Consequences

- The calendar opens on October 2026, and the reminders show what was due that
  week.
- `PAGES_SAVED_ON` in `src/db.py` and `FIXTURES_SAVED_ON` in `tests/__init__.py`
  must agree, and a test checks that they do.

## What would show this was wrong

**A listing that reads as open or closed differently from what its saved page
says.**
