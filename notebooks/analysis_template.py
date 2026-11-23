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
