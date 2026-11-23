import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import altair as alt
    import duckdb
    import marimo as mo
    import pandas as pd

    return alt, duckdb, mo, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Completed-order revenue fell 17.7% in Q3 2025, driven by fewer orders in Africa and North America
    """)
    return


@app.cell(hide_code=True)
def _():
    # Parameters: copied from the analysis notebook.
    PARAMS = {
        "start_date": "2025-07-01",
        "end_date": "2025-09-30",
        "prior_start_date": "2025-04-01",
        "prior_end_date": "2025-06-30",
    }
    return (PARAMS,)


@app.cell(hide_code=True)
def _(duckdb, mo, pd):
    # Connection: read-only, so this notebook can never write to the source.
    _db_path = mo.notebook_dir().parent / "data" / "example.duckdb"
    if not _db_path.exists():
        raise FileNotFoundError(
            f"{_db_path} not found. This example is a reference for the finished shape of a "
            "summary; point this cell at your own database to run it."
        )
    _connection = duckdb.connect(str(_db_path), read_only=True)

    def run_query(sql: str) -> pd.DataFrame:
        return _connection.execute(sql).df()

    return (run_query,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Revenue change by region

    Completed-order revenue per region in each quarter. Bars show the percentage change from Q2 to Q3, sorted from largest decline to largest gain. The table has the revenue behind each bar.
    """)
    return


@app.cell(hide_code=True)
def _(PARAMS, run_query):
    # Copied from the analysis notebook (Step 2a), reduced to completed orders.
    regional_revenue = run_query(f"""
        -- Purpose: completed revenue and order counts per region and quarter.
        -- Grain: one row per region and period (current or prior quarter).
        WITH deduped_orders AS (
            -- One row per order_id, keeping the latest version (highest updated_at).
            SELECT * FROM orders
            QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY updated_at DESC) = 1
        )
        SELECT coalesce(c.region, 'Unknown') AS region,
               CASE
                   WHEN d.order_date BETWEEN '{PARAMS["start_date"]}'
                                         AND '{PARAMS["end_date"]}' THEN 'current'
                   WHEN d.order_date BETWEEN '{PARAMS["prior_start_date"]}'
                                         AND '{PARAMS["prior_end_date"]}' THEN 'prior'
               END AS period,
               count(*) AS orders,
               sum(d.amount)::DOUBLE AS revenue
        FROM deduped_orders AS d
        -- LEFT JOIN keeps orders with no customer; their region becomes 'Unknown'.
        LEFT JOIN customers AS c ON c.customer_id = d.customer_id
        WHERE d.status = 'completed'
          AND d.order_date BETWEEN '{PARAMS["prior_start_date"]}' AND '{PARAMS["end_date"]}'
        GROUP BY 1, 2
    """)
    regional_revenue
    return (regional_revenue,)


@app.cell(hide_code=True)
def _(pd, regional_revenue):
    _prior = regional_revenue[regional_revenue["period"] == "prior"].set_index("region")
    _current = regional_revenue[regional_revenue["period"] == "current"].set_index("region")
    _by_region = pd.DataFrame(
        {
            "prior_revenue": _prior["revenue"],
            "current_revenue": _current["revenue"],
        }
    ).fillna(0)
    results = pd.concat([_by_region, _by_region.sum().rename("Total").to_frame().T])
    results["change"] = results["current_revenue"] - results["prior_revenue"]
    results["pct_change"] = results["change"] / results["prior_revenue"]
    results.index.name = "region"
    results = results.reset_index()
    return (results,)


@app.cell(hide_code=True)
def _(alt, results):
    alt.Chart(results[results["region"] != "Total"]).mark_bar(cornerRadiusEnd=4).encode(
        y=alt.Y("region:N", sort="x", title=None),
        x=alt.X(
            "pct_change:Q",
            title="Change in completed revenue, Q3 vs Q2 2025",
            axis=alt.Axis(format="%"),
        ),
        color=alt.value("#2a78d6"),
        tooltip=[
            alt.Tooltip("region:N"),
            alt.Tooltip("prior_revenue:Q", format=",.0f", title="Q2 revenue"),
            alt.Tooltip("current_revenue:Q", format=",.0f", title="Q3 revenue"),
            alt.Tooltip("pct_change:Q", format="+.1%", title="Change"),
        ],
    ).properties(width="container", height=240)
    return


@app.cell(hide_code=True)
def _(mo, results):
    mo.ui.table(
        results,
        selection=None,
        format_mapping={
            "prior_revenue": lambda v: f"{v:,.0f}",
            "current_revenue": lambda v: f"{v:,.0f}",
            "change": lambda v: f"{v:+,.0f}",
            "pct_change": lambda v: f"{v:+.1%}",
        },
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Key points

    - Completed revenue: 89,966 in Q2 to 74,038 in Q3 2025 (-17.7%).
    - Asia grew 14.2% (+2,516). Africa (-5,474) and North America (-5,157) together account for two thirds of the net decline.
    - Completed orders fell 14.8% (1,264 to 1,077), while average order value moved only -3.4% (71.18 to 68.74).
    - Counting refunded orders as well (gross booked revenue), the change is -19.4%, so the conclusion does not depend on how revenue is defined.

    ## Caveats

    - The data shows that order volume fell, not why. Whether a Q3 dip is normal seasonality was not checked, since that needs a prior-year comparison the question did not ask for.
    - Duplicate orders are resolved by keeping the latest version, which affects Q3 revenue by 1.2%.
    - The "Unknown" region (47 orders) is too small to read on its own.

    **Checks:** Totals matched an independent pandas recompute to the cent, and the monthly figures are within 0.30% of the finance ledger. Africa, North America and South America moved more than 20%, and each drop comes from fewer orders. Full detail, profiling and checks are in `analysis_example_revenue_change.py`.
    """)
    return


if __name__ == "__main__":
    app.run()
