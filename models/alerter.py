"""Alert engine for the retail forecasting pipeline.

Scans a cleaned retail DataFrame for three categories of red flags:

1. Sales anomalies  - the latest day deviates from a store/product's own
                       trailing 90-day baseline.
2. Demand decline   - a store/product's trailing 4-week average is well below
                       its prior 8-week average.
3. Low margin       - a store/product has been below the margin floor for two
                       or more consecutive months (requires profit data).

Every detector works per ``store_id`` + ``product_id`` so one store's spike
cannot hide another store's drop. Results share one contract:

    store_id, product_id, product_name, alert_type, direction, severity,
    priority, metric

``priority`` is 1 for the most urgent category (Low Margin), 2 for Demand
Decline, and 3 for Sales Anomaly. Alerts are sorted by priority, then by
severity descending within a category.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV_PATH = PROJECT_ROOT / "data" / "sample_sales.csv"

ALERT_COLUMNS = [
    "store_id",
    "product_id",
    "product_name",
    "alert_type",
    "direction",
    "severity",
    "priority",
    "metric",
]

GROUP_COLS = ["store_id", "product_id"]

LOW_MARGIN_PRIORITY = 1
DEMAND_DECLINE_PRIORITY = 2
SALES_ANOMALY_PRIORITY = 3


def _empty_alerts() -> pd.DataFrame:
    return pd.DataFrame(columns=ALERT_COLUMNS)


def _python_scalar(value):
    """Convert numpy scalars to JSON-friendly Python values."""
    return value.item() if hasattr(value, "item") else value


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "sales", "product_id"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Alert input is missing required columns: {missing}")

    prepared = df.copy()
    prepared["date"] = pd.to_datetime(prepared["date"], errors="coerce")
    prepared["sales"] = pd.to_numeric(prepared["sales"], errors="coerce")
    prepared = prepared.dropna(subset=["date", "sales", "product_id"]).copy()

    if "store_id" not in prepared.columns:
        prepared["store_id"] = 0
    if "product_name" not in prepared.columns:
        prepared["product_name"] = "Item " + prepared["product_id"].astype(str)

    return prepared


def _daily_series(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse duplicate rows into one row per store/product/date."""
    return (
        df.groupby([*GROUP_COLS, "date"], as_index=False)
        .agg(sales=("sales", "sum"), product_name=("product_name", "last"))
        .sort_values([*GROUP_COLS, "date"])
    )


def detect_anomalies(df: pd.DataFrame, threshold: float = 2.0) -> pd.DataFrame:
    """
    Flag store/products whose latest daily sales deviate more than
    ``threshold`` standard deviations from their trailing 90-day baseline.

    The latest day is excluded from the baseline so a spike cannot inflate the
    standard deviation and mask itself.
    """
    prepared = _daily_series(_prepare(df))
    if prepared.empty:
        return _empty_alerts()

    latest_date = prepared["date"].max()
    stale_after = latest_date - pd.Timedelta(days=7)
    results = []

    for (store_id, product_id), group in prepared.groupby(GROUP_COLS, sort=False):
        group = group.sort_values("date")
        if group["date"].iloc[-1] < stale_after:
            continue

        latest_sales = float(group["sales"].iloc[-1])
        cutoff = latest_date - pd.Timedelta(days=90)
        baseline = group[(group["date"] >= cutoff) & (group["date"] < latest_date)]["sales"]

        if len(baseline) < 10:
            continue

        mean = float(baseline.mean())
        std = float(baseline.std())
        if not np.isfinite(mean) or not np.isfinite(std):
            continue

        # A perfectly flat baseline has no spread; use a small relative floor
        # so a real jump is still flagged instead of dividing by zero.
        std = max(std, abs(mean) * 0.05, 1.0)
        z_score = (latest_sales - mean) / std

        if abs(z_score) <= threshold:
            continue

        direction = "spike" if z_score > 0 else "drop"
        results.append(
            {
                "store_id": _python_scalar(store_id),
                "product_id": _python_scalar(product_id),
                "product_name": str(group["product_name"].iloc[-1]),
                "alert_type": "Sales Anomaly",
                "direction": direction,
                "severity": round(abs(z_score), 2),
                "priority": SALES_ANOMALY_PRIORITY,
                "metric": (
                    f"Sales of {latest_sales:,.0f} is {abs(z_score):.1f} std devs "
                    f"{'above' if z_score > 0 else 'below'} the 90-day mean of {mean:,.0f}"
                ),
            }
        )

    return pd.DataFrame(results, columns=ALERT_COLUMNS) if results else _empty_alerts()


def detect_demand_decline(df: pd.DataFrame, decline_pct: float = 0.20) -> pd.DataFrame:
    """
    Flag store/products whose trailing 4-week average is more than
    ``decline_pct`` below their prior 8-week average.
    """
    prepared = _daily_series(_prepare(df))
    if prepared.empty:
        return _empty_alerts()

    latest_date = prepared["date"].max()
    recent_start = latest_date - pd.Timedelta(days=27)
    prior_start = recent_start - pd.Timedelta(weeks=8)
    results = []

    for (store_id, product_id), group in prepared.groupby(GROUP_COLS, sort=False):
        recent = group[group["date"] >= recent_start]["sales"]
        prior = group[(group["date"] >= prior_start) & (group["date"] < recent_start)]["sales"]

        if len(recent) < 7 or len(prior) < 14:
            continue

        recent_avg = float(recent.mean())
        prior_avg = float(prior.mean())
        if not np.isfinite(recent_avg) or not np.isfinite(prior_avg) or prior_avg <= 0:
            continue

        drop = (prior_avg - recent_avg) / prior_avg
        if drop <= decline_pct:
            continue

        results.append(
            {
                "store_id": _python_scalar(store_id),
                "product_id": _python_scalar(product_id),
                "product_name": str(group["product_name"].iloc[-1]),
                "alert_type": "Demand Decline",
                "direction": "decline",
                "severity": round(drop, 2),
                "priority": DEMAND_DECLINE_PRIORITY,
                "metric": (
                    f"4-week avg {recent_avg:,.1f} is {drop * 100:.1f}% below "
                    f"the prior 8-week avg of {prior_avg:,.1f}"
                ),
            }
        )

    return pd.DataFrame(results, columns=ALERT_COLUMNS) if results else _empty_alerts()


def detect_margin_alerts(df: pd.DataFrame, margin_threshold: float = 0.0) -> pd.DataFrame:
    """
    Flag store/products whose margin is below ``margin_threshold`` for two or
    more consecutive months, counting only the current trailing streak.
    """
    if "profit" not in df.columns:
        return _empty_alerts()

    prepared = _prepare(df)
    prepared["profit"] = pd.to_numeric(prepared["profit"], errors="coerce").fillna(0.0)
    prepared["month"] = prepared["date"].dt.to_period("M")

    monthly = (
        prepared.groupby([*GROUP_COLS, "product_name", "month"], as_index=False)
        .agg(total_sales=("sales", "sum"), total_profit=("profit", "sum"))
        .sort_values([*GROUP_COLS, "month"])
    )
    monthly["margin"] = monthly["total_profit"] / monthly["total_sales"].replace(0, np.nan)

    results = []
    for (store_id, product_id), group in monthly.groupby(GROUP_COLS, sort=False):
        margins = group["margin"].tolist()

        streak = 0
        for margin in reversed(margins):
            if pd.notna(margin) and margin < margin_threshold:
                streak += 1
            else:
                break

        if streak < 2:
            continue

        latest_margin = float(margins[-1])
        results.append(
            {
                "store_id": _python_scalar(store_id),
                "product_id": _python_scalar(product_id),
                "product_name": str(group["product_name"].iloc[-1]),
                "alert_type": "Low Margin",
                "direction": "margin",
                "severity": round(abs(latest_margin), 2),
                "priority": LOW_MARGIN_PRIORITY,
                "metric": (
                    f"Profit margin of {latest_margin * 100:.1f}% for "
                    f"{streak} consecutive months"
                ),
            }
        )

    return pd.DataFrame(results, columns=ALERT_COLUMNS) if results else _empty_alerts()


def run_all_alerts(df: pd.DataFrame, thresholds: dict | None = None) -> pd.DataFrame:
    """
    Run all three detectors and return one priority-sorted DataFrame.

    Args:
        df: Clean retail DataFrame.
        thresholds: Optional overrides with keys ``anomaly_std``,
            ``decline_pct``, and ``margin_floor``.
    """
    thresholds = thresholds or {}
    frames = [
        detect_anomalies(df, threshold=thresholds.get("anomaly_std", 2.0)),
        detect_demand_decline(df, decline_pct=thresholds.get("decline_pct", 0.20)),
        detect_margin_alerts(df, margin_threshold=thresholds.get("margin_floor", 0.0)),
    ]
    frames = [frame for frame in frames if frame is not None and not frame.empty]

    if not frames:
        return _empty_alerts()

    combined = pd.concat(frames, ignore_index=True)[ALERT_COLUMNS]
    return combined.sort_values(
        ["priority", "severity"], ascending=[True, False]
    ).reset_index(drop=True)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(PROJECT_ROOT))
    from utils.processor import load_and_clean_data

    sample = load_and_clean_data(pd.read_csv(SAMPLE_CSV_PATH))
    found = run_all_alerts(sample)
    print(found.to_string(index=False))
    print(f"Total alerts: {len(found)}")
