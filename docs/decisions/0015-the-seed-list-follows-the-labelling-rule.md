# 0015. The keyword list in this copy is a short example

Status: Accepted, 2026-10-14, and reworded for the public copy. Track C. Adds
to ADR 0003 and ADR 0011.

## Context

**The research tuned a longer keyword list to one supplier's range,** following
the labelling rule in `evaluation/labelling_rule.md`. That list describes a
real company's range, so it would help its competitors, and it stays out of
this copy (AGENTS.md, rule 1).

**The gate still needs a list to run on.** An empty list fails open and passes
everything, so the app would show no difference between keywords and models.

## Decision

- **`DEFAULT_INCLUDE_TERMS` in `src/db.py` is a short generic example:** ten
  words for rotating equipment and its spares, in English and, where CIVD
  titles use it, in Bahasa Indonesia. Put your own list in Settings, or in your
  own copy.
- **Terms are added, never removed, on thin evidence.** A removal moves
  listings out of Bidding, and a handful of relevant titles cannot show that a
  term costs more than it catches.
- **`tools/gate_terms.py` scores each term** against a labels file you supply,
  and names any term that lets through more than it catches.
- **`tests/test_filter.py` holds titles the example must catch and titles it
  must leave out**, so a later edit cannot drop one quietly.

**PREMISE:** the numbers in `evaluation/results/2026-10-29/report.txt` came
from the longer list, not this one. Anyone comparing runs their own list on
their own labels.

## Consequences

- **New seed terms reach existing databases** on the next start, and a term
  someone removed stays removed.

## What would show this was wrong

**A term whose `by_term` count shows more let through than caught** on your
labels. That term comes out, by pull request, with the numbers.
