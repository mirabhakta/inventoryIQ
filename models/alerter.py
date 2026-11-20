"""Alert engine for the retail forecasting pipeline.

Scans retail_clean.csv for three categories of red flags:
1. Sales anomalies   - unusual spikes or drops vs a product's own recent history
2. Demand decline    - products whose recent average is falling vs their longer average
3. Margin alerts     - products losing money for consecutive periods (profit data only)

run_all_alerts() combines all three detectors into one DataFrame for the API.
"""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV_PATH = PROJECT_ROOT / "data" / "sample_sales.csv"


def detect_anomalies(df: pd.DataFrame, threshold: float = 2.0) -> pd.DataFrame:
    """
    Flags products whose most recent daily sales deviate more than
    threshold standard deviations from their trailing 90-day mean.

    Args:
        df: Clean retail DataFrame loaded from retail_clean.csv
        threshold: Standard deviation cutoff (default 2.0, configurable via sidebar)

    Returns:
        DataFrame with columns: product_id, product_name, alert_type, severity, metric
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["product_id", "date"])

    results = []

    for product_id, group in df.groupby("product_id"):
        group = group.reset_index(drop=True)
        latest_date = group["date"].iloc[-1]
        cutoff = latest_date - pd.Timedelta(days=90)
        window = group[group["date"] >= cutoff]["sales"]

        if len(window) < 10:
            continue

        mean = window.mean()
        std = window.std()

        if std == 0:
            continue

        latest_sales = group["sales"].iloc[-1]
        z_score = abs((latest_sales - mean) / std)

        if z_score > threshold:
            results.append({
                "product_id": product_id,
                "product_name": group["product_name"].iloc[-1] if "product_name" in group.columns else str(group["product_id"].iloc[-1]),
                "alert_type": "Sales Anomaly",
                "severity": round(z_score, 2),
                "metric": (
                    f"Sales of {latest_sales} is {round(z_score, 1)} std devs "
                    f"from 90-day mean of {round(mean, 1)}"
                ),
            })

    return pd.DataFrame(results)


def detect_demand_decline(df: pd.DataFrame, decline_pct: float = 0.20) -> pd.DataFrame:
    """
    Flags products whose 4-week average sales have dropped more than
    decline_pct below their 12-week average.

    Args:
        df: Clean retail DataFrame loaded from retail_clean.csv
        decline_pct: Minimum drop to trigger a flag (default 0.20 = 20%, configurable)

    Returns:
        DataFrame with columns: product_id, product_name, alert_type, severity, metric
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["product_id", "date"])

    results = []

    for product_id, group in df.groupby("product_id"):
        group = group.reset_index(drop=True)
        latest_date = group["date"].iloc[-1]

        cutoff_4w = latest_date - pd.Timedelta(weeks=4)
        cutoff_12w = latest_date - pd.Timedelta(weeks=12)

        avg_4w = group[group["date"] >= cutoff_4w]["sales"].mean()
        avg_12w = group[group["date"] >= cutoff_12w]["sales"].mean()

        if pd.isna(avg_4w) or pd.isna(avg_12w) or avg_12w == 0:
            continue

        drop = (avg_12w - avg_4w) / avg_12w

        if drop > decline_pct:
            results.append({
                "product_id": product_id,
                "product_name": group["product_name"].iloc[-1] if "product_name" in group.columns else str(group["product_id"].iloc[-1]),
                "alert_type": "Demand Decline",
                "severity": round(drop, 2),
                "metric": (
                    f"4-week avg {round(avg_4w, 1)} is {round(drop * 100, 1)}% "
                    f"below 12-week avg of {round(avg_12w, 1)}"
                ),
            })

    return pd.DataFrame(results)


def detect_margin_alerts(df: pd.DataFrame, margin_threshold: float = 0.0) -> pd.DataFrame:
    """
    Flags products with a profit margin below margin_threshold for 2 or more
    consecutive monthly periods. Only runs when profit data is available.

    Args:
        df: Clean retail DataFrame loaded from retail_clean.csv
        margin_threshold: Margin floor (default 0.0 = break-even, configurable)

    Returns:
        DataFrame with columns: product_id, product_name, alert_type, severity, metric
        Returns an empty DataFrame if profit column is not present.
    """
    if "profit" not in df.columns:
        return pd.DataFrame(
            columns=["product_id", "product_name", "alert_type", "severity", "metric"]
        )

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M")

    monthly = (
        df.groupby(["product_id", "product_name", "month"])
        .agg(total_sales=("sales", "sum"), total_profit=("profit", "sum"))
        .reset_index()
    )

    monthly["margin"] = monthly["total_profit"] / monthly["total_sales"].replace(0, np.nan)
    monthly = monthly.sort_values(["product_id", "month"])

    results = []

    for product_id, group in monthly.groupby("product_id"):
        group = group.reset_index(drop=True)
        below = group["margin"] < margin_threshold

        consecutive_count = 0
        for val in below:
            if val:
                consecutive_count += 1
            else:
                consecutive_count = 0

        if consecutive_count >= 2:
            latest_margin = group["margin"].iloc[-1]
            results.append({
                "product_id": product_id,
                "product_name": group["product_name"].iloc[-1] if "product_name" in group.columns else str(group["product_id"].iloc[-1]),
                "alert_type": "Low Margin",
                "severity": round(abs(latest_margin), 2),
                "metric": (
                    f"Profit margin of {round(latest_margin * 100, 1)}% "
                    f"for {consecutive_count} consecutive periods"
                ),
            })

    return pd.DataFrame(results)


def run_all_alerts(df: pd.DataFrame, thresholds: dict | None = None) -> pd.DataFrame:
    """
    Runs all three alert detectors and combines the results.

    Args:
        df: Clean retail DataFrame
        thresholds: Optional overrides for alert sensitivity from the sidebar
                    Keys: 'anomaly_std', 'decline_pct', 'margin_floor'

    Returns:
        Combined DataFrame sorted by severity descending.
    """
    import warnings

    thresholds = thresholds or {}
    anomalies = detect_anomalies(df, threshold=thresholds.get("anomaly_std", 2.0))
    declines = detect_demand_decline(df, decline_pct=thresholds.get("decline_pct", 0.20))
    margins = detect_margin_alerts(df, margin_threshold=thresholds.get("margin_floor", 0.0))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        combined = pd.concat([anomalies, declines, margins], ignore_index=True)

    combined = combined.sort_values("severity", ascending=False).reset_index(drop=True) if not combined.empty else combined

    return combined


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(PROJECT_ROOT))
    from utils.processor import load_and_clean_data

    df = load_and_clean_data(pd.read_csv(SAMPLE_CSV_PATH))
    alerts = run_all_alerts(df)
    print(alerts.head(10))
    print(f"Total alerts: {len(alerts)}")