import pandas as pd

from models import alerter
from models.alerter import (
    detect_anomalies,
    detect_demand_decline,
    detect_margin_alerts,
    run_all_alerts,
)

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


def make_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def store_series(
    store_id: int,
    product_id: int,
    product_name: str,
    dates: pd.DatetimeIndex,
    sales: list[float],
    profit: list[float] | None = None,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "date": dates,
            "store_id": store_id,
            "product_id": product_id,
            "product_name": product_name,
            "sales": sales,
        }
    )
    if profit is not None:
        frame["profit"] = profit
    return frame


def test_detects_anomalies_per_store_and_reports_direction() -> None:
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    spike = [50.0] * 99 + [500.0]
    drop = [200.0] * 99 + [10.0]
    frame = pd.concat(
        [
            store_series(1, 101, "Shirt", dates, spike),
            store_series(2, 101, "Shirt", dates, [50.0] * 100),
            store_series(3, 102, "Mug", dates, drop),
        ],
        ignore_index=True,
    )

    alerts = detect_anomalies(frame, threshold=2.0)

    assert len(alerts) == 2
    by_store = {row["store_id"]: row for row in alerts.to_dict("records")}
    assert by_store[1]["direction"] == "spike"
    assert by_store[1]["severity"] > 5
    assert by_store[3]["direction"] == "drop"
    assert by_store[3]["severity"] > 5
    assert 2 not in by_store  # flat series is not an anomaly


def test_anomaly_baseline_excludes_the_latest_point() -> None:
    dates = pd.date_range("2024-01-01", periods=31, freq="D")
    # The spike would inflate the standard deviation if it were included in
    # the baseline, hiding the anomaly.
    frame = store_series(1, 1, "Keyboard", dates, [100.0] * 30 + [400.0])

    alerts = detect_anomalies(frame, threshold=3.0)

    assert len(alerts) == 1
    assert alerts.iloc[0]["direction"] == "spike"


def test_skips_series_without_enough_baseline_history() -> None:
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    frame = store_series(1, 1, "Lamp", dates, [10.0, 10.0, 10.0, 10.0, 90.0])

    assert detect_anomalies(frame).empty


def test_demand_decline_compares_recent_four_weeks_to_prior_eight() -> None:
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    declining = [100.0] * 92 + [50.0] * 28
    flat = [100.0] * 120
    frame = pd.concat(
        [
            store_series(1, 1, "Mug", dates, declining),
            store_series(2, 1, "Mug", dates, flat),
        ],
        ignore_index=True,
    )

    alerts = detect_demand_decline(frame, decline_pct=0.20)

    assert len(alerts) == 1
    assert alerts.iloc[0]["store_id"] == 1
    assert alerts.iloc[0]["direction"] == "decline"
    assert alerts.iloc[0]["severity"] == 0.5


def test_margin_alert_uses_only_the_trailing_streak() -> None:
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    sales = [100.0] * 120
    # Jan break-even, Feb negative, Mar/Apr positive -> no current alert.
    recovering = [0.0] * 31 + [-10.0] * 29 + [10.0] * 60
    # Mar/Apr negative -> trailing streak of 2.
    worsening = [10.0] * 60 + [-10.0] * 60
    frame = pd.concat(
        [
            store_series(1, 1, "Backpack", dates, sales, recovering),
            store_series(2, 2, "Blanket", dates, sales, worsening),
        ],
        ignore_index=True,
    )

    alerts = detect_margin_alerts(frame, margin_threshold=0.0)

    assert len(alerts) == 1
    assert alerts.iloc[0]["store_id"] == 2
    assert alerts.iloc[0]["direction"] == "margin"
    assert "2 consecutive" in alerts.iloc[0]["metric"]


def test_margin_alert_is_empty_when_profit_is_missing() -> None:
    dates = pd.date_range("2024-01-01", periods=40, freq="D")
    frame = store_series(1, 1, "Lamp", dates, [10.0] * 40)

    assert detect_margin_alerts(frame).empty


def test_run_all_alerts_sorts_by_priority_then_severity(monkeypatch) -> None:
    def fake_frame(alert_type: str, direction: str, severity: float, priority: int) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "store_id": 1,
                    "product_id": 1,
                    "product_name": "Item",
                    "alert_type": alert_type,
                    "direction": direction,
                    "severity": severity,
                    "priority": priority,
                    "metric": "",
                }
            ]
        )

    monkeypatch.setattr(
        alerter,
        "detect_anomalies",
        lambda *args, **kwargs: fake_frame("Sales Anomaly", "spike", 9.0, 3),
    )
    monkeypatch.setattr(
        alerter,
        "detect_demand_decline",
        lambda *args, **kwargs: fake_frame("Demand Decline", "decline", 0.4, 2),
    )
    monkeypatch.setattr(
        alerter,
        "detect_margin_alerts",
        lambda *args, **kwargs: fake_frame("Low Margin", "margin", 0.1, 1),
    )

    alerts = run_all_alerts(pd.DataFrame({"sales": [1.0]}))

    assert list(alerts["alert_type"]) == ["Low Margin", "Demand Decline", "Sales Anomaly"]
    assert list(alerts.columns) == ALERT_COLUMNS


def test_run_all_alerts_returns_an_empty_frame_with_columns() -> None:
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    frame = store_series(1, 1, "Lamp", dates, [10.0] * 10)

    alerts = run_all_alerts(frame)

    assert alerts.empty
    assert list(alerts.columns) == ALERT_COLUMNS
