---
name: "marimo-data-analysis"
description: "Run a data analysis or answer a data question end to end, unattended, in a marimo notebook via marimo pair: scope, profile, analyze, sanity check, and report concisely."
---

# Data Analysis in marimo (unattended)

Use this skill when the user asks a data question or requests an analysis that should end up as a reproducible marimo notebook. It builds on the `marimo-pair` skill: use marimo pair to connect to (or start) a live notebook session, test ideas in the scratchpad, and commit only validated work as cells.

## Operating mode: fully unattended
This skill runs start to finish without asking the user anything. A person may not be watching.
- Never pause to ask a question. When a decision is needed, pick the most defensible option, record the decision and the reason in the notebook, and continue.
- Anything the user would need to decide goes under "Caveats and open questions" in the summary and in the final report.
- Only one thing halts the analysis: a BLOCKER (see Step 3). Even then, finish the notebook and report; do not stop silently.
- Read-only. Never modify, delete, or write to source data.
- Never present a number that has not passed the Step 5 checks.

## Step 1: Scope the question and select tables
1. Restate the question: metric, population, time window, segments.
2. If anything is ambiguous, choose the most reasonable interpretation, and record it under "Interpretation notes" in the notebook header. If two interpretations are plausible and cheap to compute, compute both and show both.
3. Review candidate tables using the data catalog, schema listing, or `INFORMATION_SCHEMA`, plus any reference files bundled with this skill (approved sources, metric definitions).
4. For each candidate, note its grain (what one row represents), relevance, and known caveats.
5. Select the tables to use. Prefer, in order: approved or documented sources, tables at the grain the question needs, the most complete date coverage, and the fewest joins.
6. Record the selection in the notebook (Section 1): which tables were chosen, why, and which close alternatives were rejected and why.
7. Metadata inspection only until the selection is recorded.

## Step 2: Profile and review the selected sources
In the marimo scratchpad, for each selected table:
- Row count, and min/max of the relevant date column vs. the requested window.
- Column types, null rates for the columns that will be used, distinct counts.
- Primary key uniqueness at the stated grain (check for duplicates).
- Join keys: match rates between tables, and fan-out risk (does a join multiply rows?).
- Reconciliation to a known baseline where one exists.

Classify every check as OK, FLAG, or BLOCKER and record it in the Section 1 check table.

## Step 3: Handle data problems without stopping
Do not stop to ask. Classify each problem:

**FLAG (handle and continue).** The analysis can still be trusted if the problem is handled in a documented way. Apply the least aggressive reasonable fix, state it, and note the impact. Examples:
- Duplicate primary keys: dedupe with an explicit rule (e.g. keep the latest by `updated_at`), and report how many rows were affected.
- Moderate nulls in a non-key column: exclude or impute with an explicit rule, and report the share affected.
- Join fan-out: fix the join or aggregate before joining, and show the row counts before and after.
- Minor reconciliation gap within tolerance (default 1%).

**BLOCKER (the result cannot be trusted).** Examples:
- No viable table exists for the question.
- Key columns are mostly null, or the join key is unusable.
- Date coverage does not include the requested window.
- Reconciliation to the baseline is off beyond tolerance with no explanation.
- A fix would change the answer by more than the effect being measured.

On a BLOCKER: skip the analysis and sanity check results, do NOT report any headline number, and still complete the notebook with Section 1 filled in, the Status set to "Blocked", and a Summary that explains what was found, why it blocks the answer, and what is needed to unblock. Then report back (Step 6).

## Step 4: Build the notebook
Start from the template notebook below. Create the notebook file (e.g. `analysis_<topic>.py`), prototype in the scratchpad, and commit only validated cells through marimo pair.

The notebook has four sections, in this order:
1. **Data sources and assumptions checked.** Overview of the tables used, what was checked, and anything unusual (e.g. a non-unique primary key). One paragraph of 2-5 sentences, plus a flags list. The check table shows one row per check.
2. **Analysis.** The analysis cells, each with a short description above it.
3. **Sanity checks.** Overview of what was done, plus flags for any issues. One paragraph of 2-5 sentences, plus a flags list. The check table shows one row per check.
4. **Summary of findings.** One paragraph of 2-5 sentences with the answer, then key points and caveats as lists.

### Style guidelines
- Each text section is one paragraph of 2-5 sentences plus a bullet list when there are flags, issues, or key points. No more. Write "None" for an empty flags list.
- Put a 1-3 sentence markdown description above each significant step (loading, each major transformation, results).
- Add comments in SQL where they help QA and review: purpose of each CTE, grain of each result, join logic and why that join type, and the reason for each filter or exclusion.
- Comment Python only where logic is non-obvious.
- Use descriptive variable and cell names. Keep expensive loads in their own cells.
- The notebook must run top to bottom with no manual steps. Record assumptions in the notebook, not only in chat.
- Replace every `<placeholder>` in the template and delete example rows. No placeholder text may remain.
- Run `marimo check` and run the notebook top to bottom before moving on.

## Step 5: Sanity check the work
Before reporting any number, and record every check in the Section 3 check table:
- Cross-check the key result with a second, independent method (e.g. a different aggregation path, or a spot-check on a subset).
- Compare against the prior period or a known benchmark; FLAG changes beyond a threshold (default 20%) and look for a cause.
- Confirm units, sign, magnitude, and time window are plausible.
- Confirm joins did not change row counts unexpectedly and totals still reconcile.

If a check fails: investigate and fix once. If it still fails, mark it FLAG (if the answer is still usable with the caveat stated) or BLOCKER (if not), and handle as in Step 3. Never report an unverified number as settled.

## Step 6: Report back concisely
Set the notebook Status to Complete, Complete with flags, or Blocked. Then reply with:
1. **Status** and **answer**: the direct answer with key number(s) in 1-3 sentences (or, if Blocked, why no answer is given).
2. **Flags and caveats**: only those that materially affect the answer.
3. **Checks**: one line on what was verified, and anything not verified.
4. **Notebook**: the file path.
5. **Decisions made on your behalf** and **open questions**: only if there are any.

Keep it short. Put the detail in the notebook.

## Template notebook
Copy this as the starting point. Replace every `<placeholder>`, wire up `run_query`, and fill the check tables.

```python
import marimo

__generated_with = "0.23.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd

    return mo, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # <Title: the question in one line>

    **Status:** <Complete | Complete with flags | Blocked>
    **Question as interpreted:** <metric, population, time window, segments>
    **Interpretation notes:** <ambiguities that were resolved, and how. Write "None" if there were none.>
    """)
    return


@app.cell
def _():
    # Parameters: everything a rerun might change lives here.
    PARAMS = {
        "start_date": "<YYYY-MM-DD>",
        "end_date": "<YYYY-MM-DD>",
    }
    return (PARAMS,)


@app.cell
def _():
    # Connection: replace with the real read-only connection. Never write to sources.
    def run_query(sql: str):
        raise NotImplementedError("Wire up the data source")

    return (run_query,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Data sources and assumptions checked

    <One paragraph, 2-5 sentences: which tables were used and why, what one row represents in each, and which assumptions were checked (key uniqueness, null rates, date coverage, join fan-out, reconciliation to a baseline).>

    **Flags**

    - <What was found, the impact, and how it was handled. Write "None" if there are no flags.>
    """)
    return


@app.cell
def _(PARAMS, pd, run_query):
    # One row per check. status is OK, FLAG (handled and noted), or BLOCKER (result cannot be trusted).
    # Example row:
    # ("Primary key unique", "schema.orders", "FLAG", "1,204 duplicate order_id of 2.1M rows; kept latest by updated_at")
    source_check_rows = [
    ]
    source_checks = pd.DataFrame(
        source_check_rows, columns=["check", "table", "status", "detail"]
    )
    source_checks
    return (source_checks,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Analysis

    <One paragraph, 2-5 sentences: the approach, the metric definition used, and the key transformations.>
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Step 2a: <what this step does and why, 1-3 sentences>**
    """)
    return


@app.cell
def _(PARAMS, run_query):
    # Replace with the real query. Comment for QA and review: purpose, grain,
    # join logic and why, and the reason for each filter or exclusion.
    step_2a_sql = f"""
    -- Purpose: <what this query produces>
    -- Grain: <one row per ...>
    SELECT 1 AS placeholder
    """
    step_2a = run_query(step_2a_sql)
    step_2a
    return (step_2a,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Results: <what the table or chart below shows, 1-3 sentences>**
    """)
    return


@app.cell
def _(step_2a):
    # Final result table or chart that answers the question.
    results = step_2a
    results
    return (results,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Sanity checks

    <One paragraph, 2-5 sentences: the checks performed (independent recomputation, comparison with prior period or benchmark, reconciliation, plausibility of units and magnitude) and the overall outcome.>

    **Flags**

    - <Any check that failed or looked unusual, and what was done about it. Write "None" if all checks passed.>
    """)
    return


@app.cell
def _(pd, results, run_query):
    # One row per check. status is OK, FLAG, or BLOCKER.
    # Example row:
    # ("Independent recompute of total", "1,204,300", "1,204,300", "OK")
    sanity_rows = [
    ]
    sanity_checks = pd.DataFrame(
        sanity_rows, columns=["check", "expected", "observed", "status"]
    )
    sanity_checks
    return (sanity_checks,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Summary of findings

    <One paragraph, 2-5 sentences: the direct answer with the key numbers, the time window, and the population. Plain language.>

    **Key points**

    - <Finding, with number>

    **Caveats and open questions**

    - <Only items that materially affect the answer or need a human decision. Write "None" if there are none.>
    """)
    return


if __name__ == "__main__":
    app.run()
```