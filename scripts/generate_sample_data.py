#!/usr/bin/env python3
"""Generate the deterministic demo dataset used by InventoryIQ.

Output: data/sample_sales.csv

The file deliberately uses human-readable retail headers ("Order Date",
"Units Sold", ...) so it also exercises the fuzzy schema mapper. It contains
three planted signals so every dashboard panel has something to show:

* Nimbus Mug loses ~45% of demand in the final four weeks (demand decline).
* Cascade Backpack runs at a negative margin in March and April (low margin).
* Vertex Keyboard spikes 8x on the final day in store 2 (sales anomaly).

Run from the repository root:

    python scripts/generate_sample_data.py
"""

from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "sample_sales.csv"

START_DATE = date(2024, 1, 1)
DAY_COUNT = 120  # 2024-01-01 through 2024-04-29

HEADERS = [
    "Order Date",
    "Store",
    "Product",
    "Category",
    "Region",
    "Units Sold",
    "Sales",
    "Profit",
]

STORES = [
    (1, "West", 1.05),
    (2, "Central", 1.00),
    (3, "East", 0.92),
]

# name, category, base daily sales, unit price, normal margin
PRODUCTS = [
    ("Aurora Desk Lamp", "Home", 410.0, 34.0, 0.28),
    ("Nimbus Mug", "Kitchen", 260.0, 12.0, 0.31),
    ("Cascade Backpack", "Accessories", 330.0, 48.0, 0.22),
    ("Vertex Keyboard", "Electronics", 520.0, 89.0, 0.18),
    ("Solstice Blanket", "Home", 300.0, 42.0, 0.26),
]

DECLINING_PRODUCT = "Nimbus Mug"
NEGATIVE_MARGIN_PRODUCT = "Cascade Backpack"
SPIKE_PRODUCT = "Vertex Keyboard"
SPIKE_STORE = 2
SPIKE_DAY_INDEX = DAY_COUNT - 1


def demand_factor(product_name: str, day_index: int) -> float:
    """Apply the planted demand decline at the end of the series."""
    if product_name == DECLINING_PRODUCT and day_index >= DAY_COUNT - 28:
        return 0.55
    return 1.0


def margin_for(product_name: str, day_index: int) -> float:
    """Apply the planted negative-margin window (March and April)."""
    base_margin = next(margin for name, _, _, _, margin in PRODUCTS if name == product_name)
    if product_name == NEGATIVE_MARGIN_PRODUCT and day_index >= 59:
        return -0.08
    return base_margin


def daily_sales(product_name: str, base: float, day_index: int, store_factor: float, rng: random.Random) -> float:
    weekly = 1.0 + 0.10 * math.sin(2.0 * math.pi * day_index / 7.0)
    monthly = 1.0 + 0.06 * math.sin(2.0 * math.pi * day_index / 30.0)
    trend = 1.0 + 0.0008 * day_index
    noise = rng.uniform(0.93, 1.07)
    value = base * weekly * monthly * trend * store_factor * noise
    value *= demand_factor(product_name, day_index)
    return max(1.0, value)


def build_rows() -> list[list[object]]:
    rng = random.Random(20260101)
    rows: list[list[object]] = []

    for day_index in range(DAY_COUNT):
        current_date = START_DATE + timedelta(days=day_index)
        for store_id, region, store_factor in STORES:
            for product_name, category, base, unit_price, _margin in PRODUCTS:
                sales = daily_sales(product_name, base, day_index, store_factor, rng)

                if (
                    product_name == SPIKE_PRODUCT
                    and store_id == SPIKE_STORE
                    and day_index == SPIKE_DAY_INDEX
                ):
                    sales *= 8.0

                units = max(1, round(sales / unit_price))
                profit = round(sales * margin_for(product_name, day_index), 2)

                rows.append([
                    current_date.isoformat(),
                    store_id,
                    product_name,
                    category,
                    region,
                    units,
                    round(sales, 2),
                    profit,
                ])

    return rows


def main() -> None:
    rows = build_rows()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADERS)
        writer.writerows(rows)

    print(f"Wrote {len(rows):,} rows to {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
