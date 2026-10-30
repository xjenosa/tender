# Tender

**A Flask app that sorts tender listings from CIVD, the procurement portal of
SKK Migas, Indonesia's upstream oil and gas regulator.** A keyword list decides
first. A language model looks only at what the keywords missed, and can promote
a listing but never hide one. The app then tracks the listings worth bidding on,
from first sight to a submitted bid.

It is also the code behind an AIP444 group research project: on this one
triage task, how do a keyword list, a decision model (Jev) and a general LLM
(Gemini 3.5 Flash-Lite) compare?

**This copy runs on two saved CIVD pages, never the live site.**

## Who builds what

The code arrives one track at a time. Each track's owner moves it in, adds
their name below and writes their own section of this file.

| Track | Owns |
| --- | --- |
| A, the frame | the app, its pages and this repository's rules: Max (`xjenosa`) |
| B, the source | reading the saved CIVD pages |
| C, the filter | the keyword list and how it is scored |
| D, the model | the model step and the evaluation |

The rules every contributor follows, person or agent, are in `AGENTS.md`, and
what "done" means is in `docs/Acceptance.md`.
