# 0016. A listing is identified by its first attachment id

Status: Accepted, 2026-10-16. Track B.

## Context

**ADR 0002 uses an attachment id as the listing's reference.** The scraper kept
the last attachment on a card. In the 12 saved listings, 4 carry two
attachments: the first is the announcement (Pengumuman Prakualifikasi) and the
last is a declaration form (Surat Pernyataan). The id was therefore the form's,
and a buyer adding or swapping a file would change it and record one tender
twice.

**A re-upload is not rare.** One saved file is named "[rev]", and the card for
"LBS88443 : STOCK MATERIAL" says "Kategori Pengumuman: Revisi".

**Title and buyer was weighed as the key.** Across the fixtures and a live read
on 2026-10-15 no title or title and buyer pair repeated, but two live cards from
one buyer differ only by field name (rig, Field Bentayan and Field Pendopo), so
it only just holds and a buyer reissuing a title would collide.

**List types 2 and 3, read on 2026-10-15 and 2026-10-16.** Type 2 returned "0
Data". Type 3 returned one card, "Pengumuman Procurement List 2026 Original",
a yearly letter and not a tender. This matches ADR 0002 and is two days, not
weeks.

## Decision

**The first attachment's id is the listing's reference.** In all 4 two-attachment
listings it is the announcement, which is the file that belongs to the tender.

**A revised listing is the app's to recognise** by title and buyer, in
`src/db.py`. The scraper only reports what CIVD shows.

**Types 2 and 3 stay out of the app.** They were read by hand with a small
probe of the live site, which is not part of this copy.

**PREMISE:** the announcement is the first attachment on every card. If a card
shows a form first, or a revision arrives under a new id with the old one still
listed, this is re-read.

## Consequences

- `tests/test_scraper.py` checks the first attachment on a two-attachment
  listing from the saved pages.

## The weekly checks

The probe was run by hand about once a week. What it showed:

| read on | type 2 | type 3 |
|---|---|---|
| 15, 16 October | nothing ("0 Data") | one item |
| 17, 19 October | nothing | one item |
| 29 October | nothing | one item |

The one item in type 3 is "Pengumuman Procurement List 2026 Original" from SKK
Migas, showing until 29 January 2027. It is the yearly procurement-list
letter, not a tender. Five readings over two weeks have not changed the
answer in ADR 0002: type 2 is empty and type 3 is not a tender. **The weekly
check ended on 29 October 2026.**

## What would show this was wrong

**Two cards with the same title and buyer and different ids on one refresh**,
or type 2 or 3 holding a tender.
