"""Build the complete dashboard payload in one pass.

The React app renders this response directly, so aggregation, forecasting,
alerting, and benchmarking all happen where the data lives.
"""

from __future__ import annotations

import logging

import pandas as pd

from models.alerter import run_all_alerts
from services.forecast_service import get_future_forecast_frame, run_forecast_pipeline

logger = logging.getLogger(__name__)


def _native(value):
    return value.item() if hasattr(value, "item") else value


def _money(value) -> float:
    return round(float(value), 2)


def _date_range(cleaned: pd.DataFrame) -> dict | None:
    dates = pd.to_datetime(cleaned["date"], errors="coerce").dropna()
    if dates.empty:
        return None
    return {
        "start": dates.min().date().isoformat(),
        "end": dates.max().date().isoformat(),
    }


def _monthly_sales(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    monthly = (
        df.assign(month=df["date"].dt.to_period("M").astype(str))
        .groupby("month", as_index=False)["sales"]
        .sum()
        .sort_values("month")
    )
    return [
        {"month": row["month"], "total_sales": _money(row["sales"])}
        for _, row in monthly.iterrows()
    ]


def _product_rankings(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    if df.empty:
        return [], []

    grouped = (
        df.groupby(["product_id", "product_name"], as_index=False)["sales"]
        .sum()
        .sort_values(["sales", "product_name"], ascending=[False, True])
        .reset_index(drop=True)
    )

    def record(row: pd.Series) -> dict:
        return {
            "product_id": _native(row["product_id"]),
            "product": str(row["product_name"]),
            "total_sales": _money(row["sales"]),
        }

    top = [record(row) for _, row in grouped.head(10).iterrows()]

    # Only report underperformers when there are enough products that the list
    # cannot overlap with the top ten.
    bottom = []
    if len(grouped) > 10:
        remaining = grouped.iloc[10:].sort_values("sales").head(5)
        bottom = [record(row) for _, row in remaining.iterrows()]

    return top, bottom


def _group_totals(df: pd.DataFrame, column: str, label: str) -> list[dict]:
    if df.empty or column not in df.columns:
        return []
    grouped = (
        df.groupby(column, as_index=False)["sales"]
        .sum()
        .sort_values("sales", ascending=False)
    )
    return [
        {label: _native(row[column]), "total_sales": _money(row["sales"])}
        for _, row in grouped.iterrows()
    ]


def _forecast_monthly(forecast_df: pd.DataFrame) -> list[dict]:
    if forecast_df.empty:
        return []
    monthly = (
        forecast_df.assign(month=forecast_df["date"].dt.to_period("M").astype(str))
        .groupby("month", as_index=False)["prediction"]
        .sum()
        .sort_values("month")
    )
    return [
        {"month": row["month"], "prediction": _money(row["prediction"])}
        for _, row in monthly.iterrows()
    ]


def _forecast_direction(forecast_df: pd.DataFrame) -> str:
    if forecast_df.empty:
        return "flat"

    daily = forecast_df.groupby("date")["prediction"].sum().sort_index()
    if len(daily) < 2:
        return "flat"

    window = max(1, min(7, len(daily) // 2))
    first = float(daily.head(window).mean())
    last = float(daily.tail(window).mean())
    if first == 0:
        return "flat"
    if last > first * 1.05:
        return "increasing"
    if last < first * 0.95:
        return "declining"
    return "flat"


def _benchmark(filtered: pd.DataFrame) -> dict | None:
    try:
        result = run_forecast_pipeline(filtered)
    except (ValueError, ImportError) as exc:
        logger.info("Forecast benchmark unavailable: %s", exc)
        return None

    return {
        "winner": result["winner"],
        "metrics": result["metrics"],
        "table": result["comparison_table"],
    }


def analyze_retail_data(
    cleaned: pd.DataFrame,
    filtered: pd.DataFrame,
    future_days: int,
    include_benchmark: bool = True,
) -> dict:
    """
    Build the dashboard payload from the full cleaned frame and the filtered
    view. Filter options always describe the full dataset so the sidebar does
    not collapse to the current selection.
    """
    forecast_df, method = get_future_forecast_frame(filtered, future_days=future_days)
    top_products, bottom_products = _product_rankings(filtered)
    store_totals = _group_totals(filtered, "store_id", "store_id")
    category_totals = _group_totals(filtered, "category", "category")
    history = _monthly_sales(filtered)
    forecast_monthly = _forecast_monthly(forecast_df)
    forecast_total = _money(forecast_df["prediction"].sum()) if not forecast_df.empty else 0.0
    direction = _forecast_direction(forecast_df)

    alerts_df = run_all_alerts(filtered)
    alerts = alerts_df.to_dict(orient="records") if not alerts_df.empty else []

    benchmark = _benchmark(filtered) if include_benchmark and not filtered.empty else None
    winner_model = benchmark["winner"] if benchmark else None
    metrics = benchmark["metrics"] if benchmark else {}

    stores = sorted([_native(value) for value in cleaned["store_id"].dropna().unique()], key=str)
    categories = sorted(str(value) for value in cleaned["category"].dropna().unique())
    regions = (
        sorted(str(value) for value in cleaned["region"].dropna().unique())
        if "region" in cleaned.columns
        else []
    )

    return {
        "meta": {
            "row_count": int(len(filtered)),
            "total_row_count": int(len(cleaned)),
            "date_range": _date_range(cleaned),
            "stores": stores,
            "categories": categories,
            "regions": regions,
            "column_mapping": cleaned.attrs.get("column_mapping", {}),
            "optional_fields": cleaned.attrs.get("optional_fields", {}),
            "aggregation_notes": cleaned.attrs.get("aggregation_notes", []),
        },
        "kpis": {
            "total_sales": _money(filtered["sales"].sum()),
            "projected_sales": forecast_total,
            "forecast_direction": direction,
            "forecast_method": method,
            "winner_model": winner_model,
            "mae": metrics.get("mae"),
            "mase": metrics.get("mase"),
            "alert_count": len(alerts),
            "row_count": int(len(filtered)),
            "top_product": top_products[0]["product"] if top_products else None,
            "top_category": category_totals[0]["category"] if category_totals else None,
        },
        "history": {"monthly": history},
        "products": {"top": top_products, "bottom": bottom_products},
        "stores": store_totals,
        "categories": category_totals,
        "forecast": {
            "method": method,
            "future_days": future_days,
            "monthly": forecast_monthly,
            "total": forecast_total,
            "direction": direction,
        },
        "benchmark": benchmark,
        "alerts": {"items": alerts, "total": len(alerts)},
    }
