import pandas as pd
import pytest

from utils.filters import filter_retail_frame


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
            "store_id": [1, 2, 1, 2],
            "category": ["Home", "Home", "Kitchen", "Kitchen"],
            "region": ["West", "East", "West", "East"],
            "sales": [10.0, 20.0, 30.0, 40.0],
        }
    )


def test_filters_by_store_using_string_query_values() -> None:
    filtered = filter_retail_frame(frame(), stores=["2"])

    assert list(filtered["store_id"]) == [2, 2]
    assert list(filtered["sales"]) == [20.0, 40.0]


def test_filters_by_category_and_region() -> None:
    filtered = filter_retail_frame(frame(), categories=["Kitchen"], regions=["East"])

    assert list(filtered["sales"]) == [40.0]


def test_raises_when_no_rows_match() -> None:
    with pytest.raises(ValueError, match="No rows match"):
        filter_retail_frame(frame(), stores=["999"])


def test_raises_when_region_filter_is_unavailable() -> None:
    without_region = frame().drop(columns=["region"])

    with pytest.raises(ValueError, match="Region filter"):
        filter_retail_frame(without_region, regions=["West"])


def test_returns_a_copy() -> None:
    original = frame()
    filtered = filter_retail_frame(original, stores=["1"])
    filtered.loc[filtered.index[0], "sales"] = 999.0

    assert original.loc[0, "sales"] == 10.0
