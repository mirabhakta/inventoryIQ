import pandas as pd
import pytest

from services.analysis_service import _store_sort_key
from utils.filters import filter_retail_frame, normalize_store_id


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


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        (1, "1"),
        (1.0, "1"),
        ("1.0", "1"),
        (" 2 ", "2"),
        ("001", "1"),
        ("A", "A"),
        ("store-a", "store-a"),
    ],
)
def test_normalize_store_id(raw, normalized) -> None:
    assert normalize_store_id(raw) == normalized


def test_filters_float_store_ids_using_string_query_values() -> None:
    data = frame()
    data["store_id"] = [1.0, 2.0, 1.0, 2.0]

    filtered = filter_retail_frame(data, stores=["1"])

    assert list(filtered["sales"]) == [10.0, 30.0]


def test_filters_string_store_ids() -> None:
    data = frame()
    data["store_id"] = ["A", "B", "A", "B"]

    filtered = filter_retail_frame(data, stores=["A"])

    assert list(filtered["sales"]) == [10.0, 30.0]


def test_store_sort_handles_float_ids_naturally() -> None:
    assert sorted([10.0, 2.0, 1.0], key=_store_sort_key) == [1.0, 2.0, 10.0]


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
