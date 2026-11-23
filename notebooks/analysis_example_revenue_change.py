import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import altair as alt
    import duckdb
    import marimo as mo
    import pandas as pd

    return alt, duckdb, mo, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # How did completed-order revenue change in Q3 2025 vs Q2 2025, and which regions drove it?

    **Status:** Complete with flags

    **Question as interpreted:** Revenue from completed orders (cancelled and refunded orders excluded), all customers, order dates 2025-07-01 to 2025-09-30 compared with the previous quarter, 2025-04-01 to 2025-06-30, broken down by customer region.

    **Interpretation notes:** "Revenue" is ambiguous. The headline uses completed orders only. Gross booked revenue (completed plus refunded orders, before refunds are netted off) is cheap to compute, so it is shown alongside. "Previous period" is the calendar quarter immediately before the window.
    """)
    return


@app.cell
def _():
    # Parameters: everything a rerun might change lives here.
    PARAMS = {
        "start_date": "2025-07-01",
        "end_date": "2025-09-30",
        "prior_start_date": "2025-04-01",
        "prior_end_date": "2025-06-30",
        "reconciliation_tolerance": 0.01,
        "change_flag_threshold": 0.20,
    }
    return (PARAMS,)


@app.cell
def _(duckdb, mo, pd):
    # Connection: read-only, so this notebook can never write to the source.
    _db_path = mo.notebook_dir().parent / "data" / "example.duckdb"
    if not _db_path.exists():
        raise FileNotFoundError(
            f"{_db_path} not found. Build it first: uv run python scripts/seed_example_db.py"
        )
    _connection = duckdb.connect(str(_db_path), read_only=True)

    def run_query(sql: str) -> pd.DataFrame:
        return _connection.execute(sql).df()

    return (run_query,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Data sources and assumptions checked

    The analysis reads `orders` (one row per order version) and joins it to `customers` (one row per customer) for region, then reconciles to the independent `finance_monthly_summary` ledger. `orders_legacy` was rejected because it ends on 2024-09-30, before the window. Date coverage, key uniqueness, nulls, join fan-out and the ledger reconciliation were all checked; each either passed or was handled with a documented rule, and nothing blocks the answer.

    **Flags**

    - `orders` holds 127 duplicate `order_id` rows (7,127 rows for 7,000 orders). The latest version by `updated_at` is kept, which lowers Q3 revenue by 1.2% (74,925.74 without the rule, 74,038.21 with it).
    - 36 of 7,000 orders (0.5%) reference a `customer_id` missing from `customers`, and 4 of 300 customers have a null region. All of them are reported under the region "Unknown" rather than dropped.
    - Monthly revenue differs from the finance ledger by up to 0.30% across the six months compared, inside the 1% tolerance. No adjustment was made.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Step 1a: Profile every candidate table.** Row counts and date coverage for the four tables that could answer the question, to choose sources and spot coverage gaps.
    """)
    return


@app.cell
def _(run_query):
    table_profile = run_query("""
        -- Purpose: row count and date coverage of each candidate table.
        -- Grain: one row per table.
        SELECT 'orders' AS table_name, count(*) AS n_rows,
               min(order_date) AS min_date, max(order_date) AS max_date
        FROM orders
        UNION ALL
        SELECT 'orders_legacy', count(*), min(order_date), max(order_date)
        FROM orders_legacy
        UNION ALL
        SELECT 'customers', count(*), min(signup_date), max(signup_date)
        FROM customers
        UNION ALL
        SELECT 'finance_monthly_summary', count(*), min(month), max(month)
        FROM finance_monthly_summary
    """)
    table_profile
    return (table_profile,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Step 1b: Record which tables were selected and why.** `orders_legacy` looks like a close match but stops before the requested window, so it is rejected.
    """)
    return


@app.cell
def _(pd):
    table_selection = pd.DataFrame(
        [
            (
                "orders",
                "one row per order version (duplicates exist)",
                "Use",
                "Only table at order grain that covers the window; has status and updated_at.",
            ),
            (
                "customers",
                "one row per customer",
                "Use",
                "Only source of customer region; joined on customer_id.",
            ),
            (
                "finance_monthly_summary",
                "one row per month",
                "Baseline only",
                "Independent ledger of completed revenue, used to reconcile, not to compute.",
            ),
            (
                "orders_legacy",
                "one row per order version",
                "Rejected",
                "Same shape as orders but ends before the window starts.",
            ),
        ],
        columns=["table", "grain", "decision", "reason"],
    )
    table_selection
    return (table_selection,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Step 1c: Key uniqueness and null rates.** Checks whether each table's key is unique and how many nulls sit in the columns the analysis uses.
    """)
    return


@app.cell
def _(run_query):
    key_profile = run_query("""
        -- Purpose: key uniqueness and null counts for the columns the analysis uses.
        -- Grain: one row per table.
        -- n_null_used_columns counts: orders -> null amount, order_date or status;
        --                             customers -> null region.
        SELECT 'orders' AS table_name,
               count(*) AS n_rows,
               count(DISTINCT order_id) AS n_distinct_keys,
               count(*) FILTER (WHERE customer_id IS NULL) AS n_null_join_keys,
               count(*) FILTER (
                   WHERE amount IS NULL OR order_date IS NULL OR status IS NULL
               ) AS n_null_used_columns
        FROM orders
        UNION ALL
        SELECT 'customers',
               count(*),
               count(DISTINCT customer_id),
               count(*) FILTER (WHERE customer_id IS NULL),
               count(*) FILTER (WHERE region IS NULL)
        FROM customers
    """)
    key_profile
    return (key_profile,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Step 1d: Define the dedupe rule and measure its effect.** `orders` keeps an older version of some orders, so every later query reads from a deduplicated version that keeps the latest row per `order_id`. The table shows how many rows this removes and how much it moves window revenue.
    """)
    return


@app.cell
def _(PARAMS, run_query):
    deduped_orders_sql = """
        -- Purpose: one row per order_id, keeping the latest version (highest updated_at).
        -- Reason: orders holds older versions of some orders, and summing both double counts.
        -- Grain: one row per order_id.
        SELECT * FROM orders
        QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY updated_at DESC) = 1
    """

    dedupe_impact = run_query(f"""
        -- Purpose: compare current-quarter completed revenue with and without the dedupe rule.
        -- Grain: one row.
        WITH deduped_orders AS ({deduped_orders_sql})
        SELECT
            (SELECT count(*) FROM orders) AS rows_before,
            (SELECT count(*) FROM deduped_orders) AS rows_after,
            (SELECT sum(amount) FROM orders
              WHERE status = 'completed'
                AND order_date BETWEEN '{PARAMS["start_date"]}' AND '{PARAMS["end_date"]}'
            )::DOUBLE AS window_revenue_without_dedupe,
            (SELECT sum(amount) FROM deduped_orders
              WHERE status = 'completed'
                AND order_date BETWEEN '{PARAMS["start_date"]}' AND '{PARAMS["end_date"]}'
            )::DOUBLE AS window_revenue_with_dedupe
    """)
    dedupe_impact
    return deduped_orders_sql, dedupe_impact


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Step 1e: Check the join to customers.** Confirms the join does not multiply rows and counts orders that have no customer or no region.
    """)
    return


@app.cell
def _(deduped_orders_sql, run_query):
    join_check = run_query(f"""
        -- Purpose: row counts before and after joining orders to customers, plus unmatched keys.
        -- Grain: one row.
        -- LEFT JOIN so orders without a matching customer are kept rather than silently dropped.
        WITH deduped_orders AS ({deduped_orders_sql})
        SELECT
            (SELECT count(*) FROM deduped_orders) AS rows_before_join,
            count(*) AS rows_after_join,
            count(*) FILTER (WHERE c.customer_id IS NULL) AS orders_without_customer,
            count(*) FILTER (
                WHERE c.customer_id IS NOT NULL AND c.region IS NULL
            ) AS orders_with_null_region
        FROM deduped_orders AS d
        LEFT JOIN customers AS c ON c.customer_id = d.customer_id
    """)
    join_check
    return (join_check,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Step 1f: Reconcile to the finance ledger.** Compares monthly completed revenue from the deduplicated orders with the independent ledger for every month in the two quarters.
    """)
    return


@app.cell
def _(PARAMS, deduped_orders_sql, run_query):
    reconciliation = run_query(f"""
        -- Purpose: monthly completed revenue from orders vs the finance ledger.
        -- Grain: one row per month in the two quarters being compared.
        WITH deduped_orders AS ({deduped_orders_sql}),
        orders_monthly AS (
            -- Completed orders only, to match the ledger's definition
            SELECT date_trunc('month', order_date)::DATE AS month, sum(amount) AS order_revenue
            FROM deduped_orders
            WHERE status = 'completed'
            GROUP BY 1
        )
        SELECT l.month,
               o.order_revenue::DOUBLE AS order_revenue,
               l.completed_revenue::DOUBLE AS ledger_revenue,
               o.order_revenue / l.completed_revenue - 1 AS pct_gap
        FROM finance_monthly_summary AS l
        -- Inner join: a month missing on either side would show up as fewer rows than expected
        JOIN orders_monthly AS o ON o.month = l.month
        WHERE l.month BETWEEN date_trunc('month', DATE '{PARAMS["prior_start_date"]}')
                          AND date_trunc('month', DATE '{PARAMS["end_date"]}')
        ORDER BY l.month
    """)
    reconciliation
    return (reconciliation,)


@app.cell
def _(
    PARAMS,
    dedupe_impact,
    join_check,
    key_profile,
    pd,
    reconciliation,
    table_profile,
):
    # One row per check. status is OK, FLAG (handled and noted), or BLOCKER (result cannot be trusted).
    _tables = table_profile.set_index("table_name")
    _keys = key_profile.set_index("table_name")
    _dedupe = dedupe_impact.iloc[0]
    _join = join_check.iloc[0]
    _orders = _keys.loc["orders"]
    _customers = _keys.loc["customers"]

    _covers_window = _tables.loc["orders", "min_date"] <= pd.Timestamp(
        PARAMS["prior_start_date"]
    ) and _tables.loc["orders", "max_date"] >= pd.Timestamp(PARAMS["end_date"])
    _duplicate_rows = int(_orders.n_rows - _orders.n_distinct_keys)
    _dedupe_effect = _dedupe.window_revenue_with_dedupe / _dedupe.window_revenue_without_dedupe - 1
    _max_gap = reconciliation["pct_gap"].abs().max()
    _gap_status = (
        "BLOCKER"
        if _max_gap > PARAMS["reconciliation_tolerance"]
        else ("FLAG" if _max_gap > 0 else "OK")
    )

    source_check_rows = [
        (
            "Date coverage includes both quarters",
            "orders",
            "OK" if _covers_window else "BLOCKER",
            f"orders span {_tables.loc['orders', 'min_date']:%Y-%m-%d} to "
            f"{_tables.loc['orders', 'max_date']:%Y-%m-%d}; "
            f"need {PARAMS['prior_start_date']} to {PARAMS['end_date']}",
        ),
        (
            "Primary key unique",
            "orders",
            "FLAG" if _duplicate_rows else "OK",
            f"{_duplicate_rows:,} duplicate order_id rows of {int(_orders.n_rows):,}; "
            f"kept latest by updated_at, which moves current-quarter revenue by "
            f"{_dedupe_effect:+.1%}",
        ),
        (
            "Primary key unique",
            "customers",
            "OK" if _customers.n_rows == _customers.n_distinct_keys else "BLOCKER",
            f"{int(_customers.n_distinct_keys):,} distinct customer_id in "
            f"{int(_customers.n_rows):,} rows",
        ),
        (
            "Nulls in columns used",
            "orders",
            "FLAG" if _orders.n_null_used_columns else "OK",
            f"{int(_orders.n_null_used_columns):,} rows with null amount, order_date or status; "
            f"{int(_orders.n_null_join_keys):,} null customer_id",
        ),
        (
            "Nulls in columns used",
            "customers",
            "FLAG" if _customers.n_null_used_columns else "OK",
            f"{int(_customers.n_null_used_columns):,} of {int(_customers.n_rows):,} customers "
            f"have a null region; grouped as 'Unknown'",
        ),
        (
            "Join key match rate",
            "orders -> customers",
            "FLAG" if _join.orders_without_customer else "OK",
            f"{int(_join.orders_without_customer):,} of {int(_join.rows_before_join):,} orders "
            f"({_join.orders_without_customer / _join.rows_before_join:.1%}) have no customer; "
            f"kept with region 'Unknown'",
        ),
        (
            "Join fan-out",
            "orders -> customers",
            "OK" if _join.rows_before_join == _join.rows_after_join else "BLOCKER",
            f"{int(_join.rows_before_join):,} rows before the join, "
            f"{int(_join.rows_after_join):,} after",
        ),
        (
            "Reconciliation to ledger",
            "finance_monthly_summary",
            _gap_status,
            f"largest monthly gap {_max_gap:.2%} over {len(reconciliation)} months; "
            f"tolerance {PARAMS['reconciliation_tolerance']:.0%}",
        ),
    ]
    source_checks = pd.DataFrame(source_check_rows, columns=["check", "table", "status", "detail"])
    source_checks
    return (source_checks,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Analysis

    Revenue is the sum of `amount` over completed orders, after deduplicating to the latest version of each order. Orders are left-joined to customers so none are dropped, and each is assigned to the current or prior quarter by `order_date`. Gross booked revenue (completed plus refunded) is computed in the same pass as the alternative definition. Percentage change is current over prior minus one, and any region that moves by more than 20% is marked.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Step 2a: Revenue per region and period.** Deduplicates orders, attaches region, and sums completed revenue for the current and prior quarter. Gross booked revenue (completed plus refunded) is computed in the same pass for comparison.
    """)
    return


@app.cell
def _(PARAMS, deduped_orders_sql, run_query):
    regional_revenue_sql = f"""
        -- Purpose: revenue and order counts per region and period.
        -- Grain: one row per region and period (current or prior quarter).
        WITH deduped_orders AS ({deduped_orders_sql}),
        orders_in_scope AS (
            -- Grain: one row per order_id in either quarter.
            -- LEFT JOIN keeps orders with no customer; their region becomes 'Unknown'.
            -- Cancelled orders are excluded: they never produced revenue. Refunded orders are
            -- kept only to compute gross booked revenue and never count towards revenue.
            SELECT d.order_id,
                   d.amount,
                   d.status,
                   coalesce(c.region, 'Unknown') AS region,
                   CASE
                       WHEN d.order_date BETWEEN '{PARAMS["start_date"]}'
                                             AND '{PARAMS["end_date"]}' THEN 'current'
                       WHEN d.order_date BETWEEN '{PARAMS["prior_start_date"]}'
                                             AND '{PARAMS["prior_end_date"]}' THEN 'prior'
                   END AS period
            FROM deduped_orders AS d
            LEFT JOIN customers AS c ON c.customer_id = d.customer_id
            WHERE d.status IN ('completed', 'refunded')
        )
        SELECT region,
               period,
               count(*) FILTER (WHERE status = 'completed') AS orders,
               sum(amount) FILTER (WHERE status = 'completed')::DOUBLE AS revenue,
               sum(amount)::DOUBLE AS gross_booked_revenue
        FROM orders_in_scope
        WHERE period IS NOT NULL
        GROUP BY region, period
        ORDER BY region, period
    """
    regional_revenue = run_query(regional_revenue_sql)
    regional_revenue
    return (regional_revenue,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Step 2b: Compare the two quarters by region.** Reshapes the result to one row per region with prior and current revenue, the change, and the percentage change, plus a total row.
    """)
    return


@app.cell
def _(PARAMS, pd, regional_revenue):
    _prior = regional_revenue[regional_revenue["period"] == "prior"].set_index("region")
    _current = regional_revenue[regional_revenue["period"] == "current"].set_index("region")
    _by_region = pd.DataFrame(
        {
            "prior_revenue": _prior["revenue"],
            "current_revenue": _current["revenue"],
            "prior_orders": _prior["orders"],
            "current_orders": _current["orders"],
        }
    ).fillna(0)
    _total = _by_region.sum().rename("Total")
    results = pd.concat([_by_region, _total.to_frame().T])
    results["change"] = results["current_revenue"] - results["prior_revenue"]
    results["pct_change"] = results["change"] / results["prior_revenue"]
    results["beyond_threshold"] = results["pct_change"].abs() > PARAMS["change_flag_threshold"]
    results.index.name = "region"
    results = results.reset_index()
    results
    return (results,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Results: revenue change by region.** Bars show the percentage change in completed-order revenue from Q2 to Q3 2025 for each region, sorted from largest decline to largest gain.
    """)
    return


@app.cell
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
def _(mo):
    mo.md(r"""
    **Step 2c: Headline under both revenue definitions.** Totals for the two periods using completed revenue (the headline) and gross booked revenue (completed plus refunded), so a reader can see the answer does not depend on the definition.
    """)
    return


@app.cell
def _(pd, regional_revenue):
    _totals = regional_revenue.groupby("period")[["revenue", "gross_booked_revenue"]].sum()
    headline = pd.DataFrame(
        {
            "definition": ["Completed revenue (headline)", "Gross booked revenue"],
            "prior": [
                _totals.loc["prior", "revenue"],
                _totals.loc["prior", "gross_booked_revenue"],
            ],
            "current": [
                _totals.loc["current", "revenue"],
                _totals.loc["current", "gross_booked_revenue"],
            ],
        }
    )
    headline["pct_change"] = headline["current"] / headline["prior"] - 1
    headline
    return (headline,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Sanity checks

    Both quarterly totals and every regional total were recomputed in pandas (dedupe, filter, join and aggregate) and match the SQL results to the cent. Order counts, the sum of regions, the date range and the average order value all behave as expected. The overall change of -17.7% is inside the 20% threshold, but four regional changes are not, so their cause was investigated.

    **Flags**

    - Africa (-27.5%), North America (-31.5%) and South America (-20.4%) moved beyond 20%. In each case the drop comes from fewer completed orders (-29%, -26% and -21%), not from smaller orders (average order value +2%, -7% and 0%).
    - "Unknown" fell 59.1% on a small base (2,540 to 1,038 across 47 orders), partly from a lower average order value. It is too small to interpret and is left as noise.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Step 3a: Recompute the result a second way.** Pulls the raw rows for both quarters and repeats the dedupe, filter, join and aggregation in pandas, independent of the SQL used above.
    """)
    return


@app.cell
def _(PARAMS, pd, run_query):
    _raw_orders = run_query(f"""
        -- Purpose: raw order rows for both quarters, undeduplicated, for the pandas recompute.
        -- Grain: one row per order version.
        SELECT order_id, customer_id, order_date, amount, status, updated_at
        FROM orders
        WHERE order_date BETWEEN '{PARAMS["prior_start_date"]}' AND '{PARAMS["end_date"]}'
    """)
    _customers = run_query("SELECT customer_id, region FROM customers")

    _latest = _raw_orders.sort_values("updated_at").drop_duplicates("order_id", keep="last")
    _completed = _latest[_latest["status"] == "completed"].merge(
        _customers, on="customer_id", how="left", validate="many_to_one"
    )
    _completed["region"] = _completed["region"].fillna("Unknown")
    _completed["period"] = (_completed["order_date"] >= pd.Timestamp(PARAMS["start_date"])).map(
        {True: "current", False: "prior"}
    )
    _completed["amount"] = _completed["amount"].astype(float)

    recomputed = (
        _completed.groupby(["region", "period"])
        .agg(orders=("order_id", "count"), revenue=("amount", "sum"))
        .reset_index()
    )
    recomputed_date_range = (_completed["order_date"].min(), _completed["order_date"].max())
    recomputed
    return recomputed, recomputed_date_range


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Step 3b: Is the cause of any large regional change visible?** For regions whose revenue moved more than the flag threshold, splits the change into order volume and average order value.
    """)
    return


@app.cell
def _(results):
    _flagged = results[(results["region"] != "Total") & results["beyond_threshold"]].copy()
    _flagged["orders_pct_change"] = _flagged["current_orders"] / _flagged["prior_orders"] - 1
    _flagged["avg_order_value_pct_change"] = (
        _flagged["current_revenue"] / _flagged["current_orders"]
    ) / (_flagged["prior_revenue"] / _flagged["prior_orders"]) - 1
    flagged_regions = _flagged[
        ["region", "pct_change", "orders_pct_change", "avg_order_value_pct_change"]
    ].reset_index(drop=True)
    flagged_regions
    return (flagged_regions,)


@app.cell
def _(PARAMS, flagged_regions, headline, pd, recomputed, recomputed_date_range, results):
    # One row per check. status is OK, FLAG, or BLOCKER.
    _by_period = recomputed.groupby("period")["revenue"].sum()
    _sql_total = results[results["region"] == "Total"].iloc[0]
    _sql_regions = results[results["region"] != "Total"].set_index("region")
    _pandas_regions = recomputed[recomputed["period"] == "current"].set_index("region")["revenue"]
    _region_gap = (_sql_regions["current_revenue"] - _pandas_regions).abs().max()
    _overall_change = headline.loc[0, "pct_change"]
    _aov_change = (_sql_total["current_revenue"] / _sql_total["current_orders"]) / (
        _sql_total["prior_revenue"] / _sql_total["prior_orders"]
    ) - 1
    _threshold = PARAMS["change_flag_threshold"]
    _definition_gap = abs(headline.loc[0, "pct_change"] - headline.loc[1, "pct_change"])
    _in_window = recomputed_date_range[0] >= pd.Timestamp(
        PARAMS["prior_start_date"]
    ) and recomputed_date_range[1] <= pd.Timestamp(PARAMS["end_date"])

    sanity_rows = [
        (
            "Independent recompute, current quarter total",
            f"{_sql_total['current_revenue']:,.2f}",
            f"{_by_period['current']:,.2f}",
            "OK"
            if abs(_sql_total["current_revenue"] - _by_period["current"]) < 0.01
            else "BLOCKER",
        ),
        (
            "Independent recompute, prior quarter total",
            f"{_sql_total['prior_revenue']:,.2f}",
            f"{_by_period['prior']:,.2f}",
            "OK" if abs(_sql_total["prior_revenue"] - _by_period["prior"]) < 0.01 else "BLOCKER",
        ),
        (
            "Independent recompute, largest regional gap",
            "0.00",
            f"{_region_gap:,.2f}",
            "OK" if _region_gap < 0.01 else "BLOCKER",
        ),
        (
            "Order counts match after dedupe and join",
            f"{int(_sql_total['current_orders'] + _sql_total['prior_orders']):,}",
            f"{int(recomputed['orders'].sum()):,}",
            "OK"
            if _sql_total["current_orders"] + _sql_total["prior_orders"]
            == recomputed["orders"].sum()
            else "BLOCKER",
        ),
        (
            "Regional revenue sums to the total",
            f"{headline.loc[0, 'current']:,.2f}",
            f"{_sql_regions['current_revenue'].sum():,.2f}",
            "OK"
            if abs(headline.loc[0, "current"] - _sql_regions["current_revenue"].sum()) < 0.01
            else "BLOCKER",
        ),
        (
            "Rows used fall inside the two quarters",
            f"{PARAMS['prior_start_date']} to {PARAMS['end_date']}",
            f"{recomputed_date_range[0]:%Y-%m-%d} to {recomputed_date_range[1]:%Y-%m-%d}",
            "OK" if _in_window else "BLOCKER",
        ),
        (
            "Overall change vs prior quarter",
            f"within +/-{_threshold:.0%}",
            f"{_overall_change:+.1%}",
            "OK" if abs(_overall_change) <= _threshold else "FLAG",
        ),
        (
            "Average order value vs prior quarter (units and magnitude)",
            f"within +/-{_threshold:.0%}",
            f"{_aov_change:+.1%}",
            "OK" if abs(_aov_change) <= _threshold else "FLAG",
        ),
        (
            "Regional changes vs prior quarter",
            f"all within +/-{_threshold:.0%}",
            ", ".join(f"{r.region} {r.pct_change:+.1%}" for r in flagged_regions.itertuples())
            or "all within threshold",
            "FLAG" if len(flagged_regions) else "OK",
        ),
        (
            "Revenue definitions agree on direction and size",
            "gap under 2 percentage points",
            f"{_definition_gap * 100:.1f} percentage points",
            "OK" if _definition_gap < 0.02 else "FLAG",
        ),
    ]
    sanity_checks = pd.DataFrame(sanity_rows, columns=["check", "expected", "observed", "status"])
    sanity_checks
    return (sanity_checks,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Summary of findings

    Completed-order revenue fell 17.7% from 89,966 in Q2 2025 to 74,038 in Q3 2025, a drop of 15,928. Asia was the only region to grow, while every other region declined. The fall comes from fewer completed orders rather than smaller ones, and gross booked revenue tells the same story (-19.4%).

    **Key points**

    - Completed revenue: 89,966 in Q2 to 74,038 in Q3 2025 (-17.7%).
    - Asia grew 14.2% (+2,516). Africa (-5,474) and North America (-5,157) together account for two thirds of the net decline.
    - Completed orders fell 14.8% (1,264 to 1,077), while average order value moved only -3.4% (71.18 to 68.74).
    - On gross booked revenue (completed plus refunded) the change is -19.4%, so the conclusion does not depend on how revenue is defined.

    **Caveats and open questions**

    - The data shows that order volume fell, not why. Whether a Q3 dip is normal seasonality was not checked, since that needs a prior-year comparison the question did not ask for.
    - The rule for duplicate orders (keep the latest version) affects Q3 revenue by 1.2%. If the source system treats the older version as authoritative, the totals would change by about that much.
    - Revenue for "Unknown" region customers (47 orders in the two quarters) is unreliable as a segment and should not be read on its own.
    """)
    return


if __name__ == "__main__":
    app.run()
