# marimo-data-analysis-skill

A verbatim copy of the `marimo-data-analysis` Claude skill, plus the notebooks it describes: a
blank template to start every analysis from, and a complete worked example that follows the skill's
conventions.

## Layout

Everything the skill ships is in `skill/`; the rest of the repo is documentation and a Makefile.

- `skill/SKILL.md` – the skill, unmodified. Its "Template notebook" section is the source of the template.
- `skill/notebooks/analysis_template.py` – the blank starting point, identical to the code block in
  `skill/SKILL.md`. Copy it to `analysis_<topic>.py`, replace every `<placeholder>`, wire up
  `run_query`, and fill in the two check tables.
- `skill/notebooks/analysis_example_revenue_change.py` – a finished analysis: *how did completed-order
  revenue change in Q3 2025 vs Q2 2025, and which regions drove it?* Every placeholder is filled in.
  It reads a DuckDB database that is not included, so treat it as a reference for the finished shape
  of an analysis rather than something to run.

## Local testing

`make install` copies `skill/` to `~/.claude/skills/marimo-data-analysis/`. Restart Claude Code to pick it up.

## What the example demonstrates

| Skill step | In the example |
| ---------- | -------------- |
| 1. Scope and select tables | Four candidates profiled; `orders_legacy` rejected because it ends before the window; the finance ledger kept as a reconciliation baseline only |
| 2. Profile sources | Row counts and date coverage, key uniqueness, null rates, join fan-out, ledger reconciliation |
| 3. Handle problems | FLAGs, not stops: duplicate `order_id` rows (dedupe rule stated and its effect measured), unmatched customers and null regions (kept as "Unknown"), a small ledger gap (inside tolerance) |
| 4. Build the notebook | Four sections in order, one short paragraph plus flags list per text section, SQL comments for purpose / grain / join logic / filters, parameters in one cell, read-only connection |
| 5. Sanity check | Independent pandas recompute (total and per region), row counts, date range, prior-period comparison with a 20% threshold, cause analysis for flagged regions |
| 6. Report | Status "Complete with flags"; the notebook's Section 4 is the written report |

The example also computes both plausible definitions of "revenue" (completed only, and gross booked
before refunds) and shows both, as Step 1 asks when two interpretations are cheap to compute.

## Notes

- Prose in the example notebook is written out, not generated, so the numbers quoted in the text
  belong to the data it was written against.
