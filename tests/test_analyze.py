import pandas as pd
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def retail_frame(periods: int = 120) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=periods, freq="D")
    rows = []
    for store, region in [(1, "West"), (2, "East")]:
        for product, category, base, declines in [
            ("Mug", "Kitchen", 100.0, True),
            ("Lamp", "Home", 200.0, False),
        ]:
            for index, current_date in enumerate(dates):
                sales = base * (0.5 if declines and index >= periods - 28 else 1.0)
                rows.append(
                    {
                        "Order Date": current_date,
                        "Store": store,
                        "Product": product,
                        "Category": category,
                        "Region": region,
                        "Sales": sales,
                    }
                )
    return pd.DataFrame(rows)


def upload(frame: pd.DataFrame) -> dict:
    return {"file": ("sales.csv", frame.to_csv(index=False).encode("utf-8"), "text/csv")}


def analyze(frame: pd.DataFrame, **params) -> dict:
    response = client.post("/analyze", files=upload(frame), params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_analyze_returns_the_full_dashboard_payload() -> None:
    body = analyze(retail_frame(), future_days=14, include_benchmark="false")

    assert body["meta"]["total_row_count"] == 480
    assert body["meta"]["row_count"] == 480
    assert body["meta"]["stores"] == [1, 2]
    assert body["meta"]["categories"] == ["Home", "Kitchen"]
    assert body["meta"]["regions"] == ["East", "West"]
    assert body["meta"]["date_range"] == {"start": "2024-01-01", "end": "2024-04-29"}

    assert body["kpis"]["total_sales"] == 69200.0
    assert body["kpis"]["alert_count"] == 2
    assert body["kpis"]["top_product"] == "Lamp"
    assert body["kpis"]["top_category"] == "Home"

    assert len(body["history"]["monthly"]) == 4
    assert body["history"]["monthly"][0] == {"month": "2024-01", "total_sales": 18600.0}

    assert body["products"]["top"][0]["product"] == "Lamp"
    assert body["products"]["top"][0]["total_sales"] == 48000.0
    assert body["products"]["bottom"] == []

    assert body["forecast"]["future_days"] == 14
    assert body["forecast"]["method"] in {"lightgbm_global_lag", "simple_last_value_future"}
    assert body["forecast"]["total"] > 0
    assert body["forecast"]["monthly"]
    assert body["kpis"]["projected_sales"] == body["forecast"]["total"]

    assert body["alerts"]["total"] == 2
    assert {alert["store_id"] for alert in body["alerts"]["items"]} == {1, 2}
    assert {alert["direction"] for alert in body["alerts"]["items"]} == {"decline"}

    assert body["benchmark"] is None


def test_analyze_applies_filters_but_keeps_full_filter_options() -> None:
    body = analyze(retail_frame(), future_days=7, include_benchmark="false", store=["1"])

    assert body["meta"]["row_count"] == 240
    assert body["meta"]["total_row_count"] == 480
    assert body["meta"]["stores"] == [1, 2]
    assert body["kpis"]["total_sales"] == 34600.0
    assert {alert["store_id"] for alert in body["alerts"]["items"]} == {1}


def test_analyze_filters_by_region() -> None:
    body = analyze(
        retail_frame(), future_days=7, include_benchmark="false", region=["West"]
    )

    assert body["kpis"]["total_sales"] == 34600.0
    assert {alert["store_id"] for alert in body["alerts"]["items"]} == {1}


def test_analyze_includes_the_benchmark_by_default() -> None:
    body = analyze(retail_frame(), future_days=7)

    assert body["benchmark"] is not None
    assert body["benchmark"]["winner"]
    assert body["benchmark"]["table"]
    assert body["kpis"]["mae"] is not None
    assert body["kpis"]["winner_model"] == body["benchmark"]["winner"]


def test_analyze_rejects_horizon_over_the_cap() -> None:
    response = client.post("/analyze", files=upload(retail_frame()), params={"future_days": 181})

    assert response.status_code == 422


def test_analyze_rejects_filters_with_no_rows() -> None:
    response = client.post(
        "/analyze",
        files=upload(retail_frame()),
        params={"store": ["999"], "include_benchmark": "false"},
    )

    assert response.status_code == 422
    assert "No rows match" in response.json()["detail"]
