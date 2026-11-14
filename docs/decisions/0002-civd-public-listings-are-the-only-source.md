# 0002. CIVD's public listings are the only source, read from saved pages

Status: Accepted, 2026-10-11.

## Context

**CIVD, SKK Migas's procurement portal, publishes its prequalification
invitations without a login.** Its list shows six cards a page, about forty at
a time. Each card carries a title, the buying company, the date it stops
showing, whether it is goods (Barang) or services (Jasa), the business fields,
and an attachment id.

**This copy is public.** If it read the live site, everyone who ran the code
would send traffic to CIVD, and the tests would change whenever CIVD did.

## Decision

**CIVD's prequalification invitations are the only source, and this copy reads
them from two pages saved on 11 October 2026,** in `fixtures/`. Python's own
HTML parser reads them: no network, no browser, no login, no extra dependency.

- **Refresh loads the saved pages,** so a second Refresh finds nothing new.
- **List type 1 only.** Type 2 returned nothing and type 3 is the yearly
  procurement-list letter, not a tender (ADR 0016).
- **The attachment id is the listing's reference**, since CIVD shows no tender
  number. ADR 0016 says which attachment.
- **The date a card stops showing is stored as its deadline.** For a
  prequalification invitation that is when registration closes.

**PREMISE:** the saved pages show the markup CIVD used in October 2026. This
copy only ever reads those pages, so a later change on CIVD does not break it.
Reading the live site again would need a new decision.

## Consequences

- The tests and the app run on the same two pages, so nothing needs a network.
- Setup is `pip install Flask` and nothing else.

## What would show this was wrong

**A refresh that reads fewer cards than the saved pages hold**, or a deadline
that does not match its card.
