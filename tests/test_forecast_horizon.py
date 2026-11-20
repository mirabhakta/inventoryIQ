import pandas as pd
import pytest

from services.forecast_service import get_future_forecast
from utils.forecasting import MAX_FUTURE_DAYS


def medium_dataset() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=180, freq="D")
    rows = []
    for store, item, base in [(1, 101, 120.0), (2, 102, 80.0)]:
        for index, current_date in enumerate(dates):
            weekly = 1.0 + 0.15 * ((index % 7) - 3) / 3.0
            sales = base * weekly + (index % 5)
            rows.append(
                {
                    "date": current_date,
                    "store": store,
                    "item": item,
                    "sales": round(sales, 2),
                }
            )
    return pd.DataFrame(rows)


def test_future_forecast_uses_lightgbm_when_history_supports_lags() -> None:
    result = get_future_forecast(medium_dataset(), future_days=30)

    assert result["method"] == "lightgbm_global_lag"
    assert len(result["forecast_records"]) == 30 * 2
    predictions = {record["prediction"] for record in result["forecast_records"]}
    assert len(predictions) > 1


def test_future_forecast_keeps_simple_fallback_for_tiny_history() -> None:
    dates = pd.date_range("2024-01-01", periods=6, freq="D")
    frame = pd.DataFrame(
        {
            "date": dates,
            "store": [1] * 6,
            "item": [101] * 6,
            "sales": [10, 12, 11, 13, 14, 15],
        }
    )

    result = get_future_forecast(frame, future_days=7)

    assert result["method"] == "simple_last_value_future"
    assert len(result["forecast_records"]) == 7


@pytest.mark.parametrize("future_days", [0, -1, MAX_FUTURE_DAYS + 1])
def test_future_forecast_rejects_out_of_range_horizons(future_days: int) -> None:
    with pytest.raises(ValueError, match=f"between 1 and {MAX_FUTURE_DAYS}"):
        get_future_forecast(medium_dataset(), future_days=future_days)
