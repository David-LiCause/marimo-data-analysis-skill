import marimo

__generated_with = "0.23.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd

    return mo, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # <Title: the answer in one line, with the key number>
    """)
    return


@app.cell(hide_code=True)
def _():
    # Parameters: copied from the analysis notebook. Keep only the ones the cells below use.
    PARAMS = {
        "start_date": "<YYYY-MM-DD>",
        "end_date": "<YYYY-MM-DD>",
    }
    return (PARAMS,)


@app.cell(hide_code=True)
def _():
    # Connection: the same read-only connection as the analysis notebook. Never write to sources.
    def run_query(sql: str):
        raise NotImplementedError("Wire up the data source")

    return (run_query,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## <Key result 1: a short heading>

    <1-2 sentences: what the table or chart below shows and how to read it.>
    """)
    return


@app.cell(hide_code=True)
def _(PARAMS, run_query):
    # Copied from the analysis notebook: only the query behind this result, with its comments.
    result_1_sql = f"""
    -- Purpose: <what this query produces>
    -- Grain: <one row per ...>
    SELECT 1 AS placeholder
    """
    result_1 = run_query(result_1_sql)
    result_1
    return (result_1,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Key points

    - <Finding, with number. Same numbers as the analysis notebook.>

    ## Caveats

    - <Only items that materially affect how the answer should be read. Write "None" if there are none.>

    **Checks:** <One line: which checks passed, and any that were flagged.> Full detail, profiling and checks are in `<analysis_topic.py>`.
    """)
    return


if __name__ == "__main__":
    app.run()
