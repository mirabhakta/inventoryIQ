import pandas as pd

from services.forecast_service import get_aggregate_future_forecast_frame


def aggregate_source(periods: int = 120) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=periods, freq="D")
    rows = []
    for store, item, base in [(1, 101, 100.0), (2, 102, 60.0)]:
        for index, current_date in enumerate(dates):
            rows.append(
                {
                    "date": current_date,
                    "store": store,
                    "item": item,
                    "sales": base + (index % 7) * 3,
                }
            )
    return pd.DataFrame(rows)


def test_aggregate_forecast_trains_one_total_series() -> None:
    forecast, method = get_aggregate_future_forecast_frame(aggregate_source(), future_days=14)

    assert method == "lightgbm_global_lag"
    assert len(forecast) == 14
    assert forecast["store"].unique().tolist() == [0]
    assert forecast["item"].unique().tolist() == [0]
    assert (forecast["prediction"] > 0).all()


def test_aggregate_forecast_falls_back_for_tiny_history() -> None:
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    frame = pd.DataFrame(
        {"date": dates, "store": 1, "item": 101, "sales": [10, 12, 11, 13, 14]}
    )

    forecast, method = get_aggregate_future_forecast_frame(frame, future_days=7)

    assert method == "simple_last_value_future"
    assert len(forecast) == 7
    assert forecast["prediction"].nunique() == 1
