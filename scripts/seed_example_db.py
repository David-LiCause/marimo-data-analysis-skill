"""Build data/example.duckdb: a small synthetic orders database for the example notebook.

Deterministic (fixed seed) and safe to re-run. The data is deliberately imperfect so the example
notebook has real flags to handle:

- orders has duplicate order_id rows (an older version of the order plus the latest one)
- some orders reference customers that do not exist in customers
- some customers have a null region
- finance_monthly_summary is the "known baseline" revenue ledger, off by a small noise term
- orders_legacy is a close alternative table that stops before the analysis window
"""

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "example.duckdb"
SEED = 42
N_CUSTOMERS = 300
N_ORDERS = 7000
DUPLICATE_RATE = 0.02  # share of orders that also have an older version
ORPHAN_RATE = 0.005  # share of orders whose customer_id is not in customers
NULL_REGION_RATE = 0.02
BASELINE_NOISE = 0.003  # finance ledger differs from the order data by up to +/-0.3%
REGIONS = ["North America", "Europe", "Asia", "South America", "Africa"]
FIRST_MONTH = date(2024, 1, 1)
N_MONTHS = 21  # 2024-01 .. 2025-09
LEGACY_CUTOFF = date(2024, 9, 30)


def month_start(index: int) -> date:
    return date(FIRST_MONTH.year + (index // 12), index % 12 + 1, 1)


def build_customers(rng: random.Random) -> list[tuple]:
    rows = []
    for customer_id in range(1, N_CUSTOMERS + 1):
        region = None if rng.random() < NULL_REGION_RATE else rng.choice(REGIONS)
        signup = date(2024, 1, 1) + timedelta(days=int(rng.triangular(0, 450, 0)))
        rows.append((customer_id, f"Customer {customer_id:03d}", region, signup))
    return rows


def build_orders(rng: random.Random, customers: list[tuple]) -> list[tuple]:
    month_weights = [1 + 0.04 * i for i in range(N_MONTHS)]
    rows = []
    order_id = 0
    while order_id < N_ORDERS:
        month = month_start(rng.choices(range(N_MONTHS), weights=month_weights)[0])
        next_month = date(month.year + month.month // 12, month.month % 12 + 1, 1)
        order_date = month + timedelta(days=rng.randrange((next_month - month).days))
        customer_id, _name, region, signup = rng.choice(customers)
        # Asia picks up sharply from July 2025; accept other regions less often from then on
        if order_date >= date(2025, 7, 1) and region != "Asia" and rng.random() < 0.3:
            continue
        if signup > order_date:
            continue
        order_id += 1
        if rng.random() < ORPHAN_RATE:
            customer_id = 9000 + order_id
        amount = round(rng.lognormvariate(4.0, 0.7), 2)
        status = rng.choices(["completed", "cancelled", "refunded"], weights=[88, 7, 5])[0]
        updated_at = datetime.combine(order_date, datetime.min.time()) + timedelta(
            hours=rng.randint(1, 72)
        )
        if rng.random() < DUPLICATE_RATE:
            # Older version still shows the order as completed; the latest one is the truth
            older = updated_at - timedelta(hours=rng.randint(1, 24))
            rows.append((order_id, customer_id, order_date, amount, "completed", older))
            status = rng.choice(["cancelled", "refunded"])
        rows.append((order_id, customer_id, order_date, amount, status, updated_at))
    return rows


def build_baseline(rng: random.Random, orders: list[tuple]) -> list[tuple]:
    latest: dict[int, tuple] = {}
    for row in orders:
        if row[0] not in latest or row[5] > latest[row[0]][5]:
            latest[row[0]] = row
    totals: dict[date, float] = {}
    for _id, _cust, order_date, amount, status, _upd in latest.values():
        if status == "completed":
            key = order_date.replace(day=1)
            totals[key] = totals.get(key, 0.0) + amount
    return [
        (month, round(total * (1 + rng.uniform(-BASELINE_NOISE, BASELINE_NOISE)), 2))
        for month, total in sorted(totals.items())
    ]


def main() -> None:
    rng = random.Random(SEED)
    customers = build_customers(rng)
    orders = build_orders(rng, customers)
    baseline = build_baseline(rng, orders)
    legacy = [r for r in orders if r[2] <= LEGACY_CUTOFF]

    DB_PATH.parent.mkdir(exist_ok=True)
    DB_PATH.unlink(missing_ok=True)
    con = duckdb.connect(str(DB_PATH))
    order_columns = (
        "order_id INTEGER, customer_id INTEGER, order_date DATE, amount DECIMAL(10, 2), "
        "status VARCHAR, updated_at TIMESTAMP"
    )
    con.execute(
        "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name VARCHAR, region VARCHAR, "
        "signup_date DATE)"
    )
    con.execute(f"CREATE TABLE orders ({order_columns})")
    con.execute(f"CREATE TABLE orders_legacy ({order_columns})")
    con.execute(
        "CREATE TABLE finance_monthly_summary (month DATE, completed_revenue DECIMAL(14, 2))"
    )
    con.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers)
    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", orders)
    con.executemany("INSERT INTO orders_legacy VALUES (?, ?, ?, ?, ?, ?)", legacy)
    con.executemany("INSERT INTO finance_monthly_summary VALUES (?, ?)", baseline)
    con.close()
    print(f"Wrote {DB_PATH} ({len(orders)} order rows, {len(customers)} customers)")


if __name__ == "__main__":
    main()
