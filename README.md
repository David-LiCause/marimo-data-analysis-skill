# marimo-data-analysis-skill

A verbatim copy of the `marimo-data-analysis` Claude skill, plus the notebooks it describes: a
blank template to start every analysis from, and a complete worked example that follows the skill's
conventions.

## Layout

- `SKILL.md` – the skill, unmodified. Its "Template notebook" section is the source of the template.
- `notebooks/analysis_template.py` – the blank starting point, byte-identical to the code block in
  `SKILL.md` (a test enforces this). Copy it to `analysis_<topic>.py`, replace every `<placeholder>`,
  wire up `run_query`, and fill in the two check tables.
- `notebooks/analysis_example_revenue_change.py` – a finished analysis: *how did completed-order
  revenue change in Q3 2025 vs Q2 2025, and which regions drove it?* Every placeholder is filled in.
- `scripts/seed_example_db.py` – builds `data/example.duckdb`, the synthetic database the example
  reads. Deterministic, safe to re-run. `data/` is git-ignored.
- `tests/` – smoke tests (template matches `SKILL.md`, example runs with no blockers).

## Quickstart

```bash
uv sync
uv run python scripts/seed_example_db.py
uv run marimo edit notebooks/analysis_example_revenue_change.py
```

Checks, as the skill requires before moving on:

```bash
uv run marimo check notebooks
uv run python notebooks/analysis_example_revenue_change.py   # runs top to bottom headless
uv run pytest && uv run ruff check .
```

## What the example demonstrates

The seeded data is deliberately imperfect so each step of the skill has something to do:

| Skill step | In the example |
| ---------- | -------------- |
| 1. Scope and select tables | Four candidates profiled; `orders_legacy` rejected because it ends before the window; the finance ledger kept as a reconciliation baseline only |
| 2. Profile sources | Row counts and date coverage, key uniqueness, null rates, join fan-out, ledger reconciliation |
| 3. Handle problems | FLAGs, not stops: 127 duplicate `order_id` rows (dedupe rule stated and its 1.2% effect measured), unmatched customers and null regions (kept as "Unknown"), a 0.30% ledger gap (inside tolerance) |
| 4. Build the notebook | Four sections in order, one short paragraph plus flags list per text section, SQL comments for purpose / grain / join logic / filters, parameters in one cell, read-only connection |
| 5. Sanity check | Independent pandas recompute (total and per region), row counts, date range, prior-period comparison with a 20% threshold, cause analysis for flagged regions (order volume, not order value) |
| 6. Report | Status "Complete with flags"; the notebook's Section 4 is the written report |

The example also computes both plausible definitions of "revenue" (completed only, and gross booked
before refunds) and shows both, as Step 1 asks when two interpretations are cheap to compute.

## Notes

- Prose in the example notebook is written out, not generated, so if you change `PARAMS` or the
  seed, the numbers quoted in the text need updating. The tables and checks are always computed.
- This project follows the `marimo-sandbox` conventions (`uv`, `package = false`) rather than the
  `templates/python-project` layout, because it holds notebooks and a skill rather than a package.
  The skill asks for SQL comments for review, so, unlike `marimo-sandbox`, the notebooks use them.
