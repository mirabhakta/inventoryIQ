"""Shared dashboard filters for cleaned retail frames."""

from __future__ import annotations

import pandas as pd


def normalize_store_id(value) -> str:
    """
    Canonicalize store identifiers for comparisons.

    CSVs often produce float IDs (``1.0``) while the browser sends the string
    ``"1"``. Text IDs are preserved as-is.
    """
    text = str(value).strip()
    try:
        number = float(text)
    except (TypeError, ValueError):
        return text
    if number.is_integer():
        return str(int(number))
    return text


def filter_retail_frame(
    df: pd.DataFrame,
    stores: list[str] | None = None,
    categories: list[str] | None = None,
    regions: list[str] | None = None,
) -> pd.DataFrame:
    """
    Apply the dashboard filters to a cleaned frame.

    Store IDs are normalized so numeric and text IDs work with the same query
    contract. Raises ``ValueError`` when a filter is unavailable or selects no
    rows.
    """
    filtered = df

    if stores:
        wanted_stores = {normalize_store_id(store) for store in stores}
        filtered = filtered[filtered["store_id"].map(normalize_store_id).isin(wanted_stores)]

    if categories:
        filtered = filtered[filtered["category"].isin(categories)]

    if regions:
        if "region" not in filtered.columns:
            raise ValueError("Region filter is not available for this dataset.")
        filtered = filtered[filtered["region"].isin(regions)]

    if filtered.empty:
        raise ValueError("No rows match the selected filters.")

    return filtered.copy()
