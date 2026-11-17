import os
import sys
import csv
import argparse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

import db
import tender_filter

LABELS = os.path.join(REPO_ROOT, "evaluation", "labels.csv")
SCORED = {"0": False, "1": True}


def load_labelled(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [(r["title"], SCORED[r["label"].strip()]) for r in csv.DictReader(f) if r["label"].strip() in SCORED]


def _share(value):
    return "n/a" if value is None else f"{value:.2f}"


def report(labelled, terms):
    s = tender_filter.gate_scores(labelled, terms)
    by_term = s["by_term"]
    relevant = sum(1 for _title, r in labelled if r)
    lines = [f"{len(labelled)} labelled listings, {relevant} relevant",
             f"recall {_share(s['recall'])}, precision {_share(s['precision'])}: caught {len(s['caught'])}, "
             f"missed {len(s['missed'])}, let through {len(s['let_through'])}",
             "",
             "caught  let through  term"]
    for term in sorted(by_term, key=lambda t: (-by_term[t]["let_through"], -by_term[t]["caught"], t)):
        lines.append(f"{by_term[term]['caught']:>6}  {by_term[term]['let_through']:>11}  {term}")
    unmatched = [t for t in terms if t not in by_term]
    lines += ["",
              f"{len(unmatched)} of {len(terms)} terms matched no labelled title",
              "lets through more than it catches: " + (", ".join(tender_filter.loose_terms(by_term)) or "none"),
              "relevant titles no term caught: " + (str(len(s["missed"])) if s["missed"] else "none")]
    lines += [f"  {title}" for title in s["missed"]]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Score each seed keyword against the labelled listings, by title.")
    ap.add_argument("--labels", default=LABELS, help="a labels.csv, or a copy of it")
    args = ap.parse_args()
    labelled = load_labelled(args.labels)
    if not labelled:
        sys.exit(f"no row in {args.labels} has a label of 0 or 1")
    print(report(labelled, db.DEFAULT_INCLUDE_TERMS))


if __name__ == "__main__":
    main()
