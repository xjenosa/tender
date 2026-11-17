# 0004. Keywords are learned from submitted bids

Status: Accepted, 2026-10-11.

## Context

**A keyword list kept by hand falls behind.** The app needs a sign that a kind
of tender is worth seeing, without anyone editing the list.

## Decision

**Moving a card into Submitted teaches the filter.** The distinctive words of
its title, stopwords and short words removed, join the keyword list, at most
six per title.

- **Add only.** Learning never removes a keyword.
- **A removed keyword waits five business days** before learning may add it
  again. A person adding it by hand skips the wait.
- **Learned keywords show with a dashed outline** in Settings.

**PREMISE:** submitting a bid is the strongest sign that a kind of tender is
worth seeing. If the group finds that learning floods the list, this is re-read.

## Consequences

- Each keyword keeps where it came from, a person or a submitted bid, and a
  removed one keeps the day its wait ends, so the wait survives a restart.

## What would show this was wrong

**The keyword list filling with words that match services nobody bids on.**
