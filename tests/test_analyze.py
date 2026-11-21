import pandas as pd
from fastapi.testclient import TestClient

from api import analyze_routes
from main import app
from services import analysis_service, dataset_cache

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


def large_frame(rows: int = 60_000) -> pd.DataFrame:
    stores, products = 10, 10
    days = rows // (stores * products)
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    records = []
    for store in range(1, stores + 1):
        for product in range(1, products + 1):
            for index, current_date in enumerate(dates):
                records.append(
                    {
                        "Order Date": current_date,
                        "Store": store,
                        "Product": f"Item {product}",
                        "Category": "Home" if product <= 5 else "Kitchen",
                        "Region": "West" if store <= 5 else "East",
                        "Sales": 100 + (index % 20),
                    }
                )
    return pd.DataFrame(records)


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
    assert body["benchmark_note"] is None


def test_analyze_skips_the_benchmark_for_large_datasets(monkeypatch) -> None:
    monkeypatch.setattr(analysis_service, "MAX_BENCHMARK_ROWS", 10)

    body = analyze(retail_frame(), future_days=7)

    assert body["benchmark"] is None
    assert body["kpis"]["mae"] is None
    assert "skipped" in body["benchmark_note"].lower()


def test_analyze_accepts_float_store_ids_in_filters() -> None:
    frame = retail_frame()
    frame["Store"] = frame["Store"].astype(float)

    body = analyze(frame, future_days=7, include_benchmark="false", store=["1"])

    assert body["meta"]["row_count"] == 240
    assert body["kpis"]["total_sales"] == 34600.0


def test_analyze_accepts_a_60k_row_upload_and_skips_the_benchmark() -> None:
    body = analyze(large_frame(), future_days=7, include_benchmark="true")

    assert body["meta"]["row_count"] == 60_000
    assert body["meta"]["stores"] == list(range(1, 11))
    assert body["benchmark"] is None
    assert "skipped" in body["benchmark_note"].lower()
    assert body["forecast"]["total"] > 0


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


def test_analyze_reuses_the_cached_payload(monkeypatch) -> None:
    calls = {"count": 0}
    real_analyze = analyze_routes.analyze_retail_data

    def counted(*args, **kwargs):
        calls["count"] += 1
        return real_analyze(*args, **kwargs)

    monkeypatch.setattr(analyze_routes, "analyze_retail_data", counted)
    frame = retail_frame()

    first = analyze(frame, future_days=7, include_benchmark="false")
    second = analyze(frame, future_days=7, include_benchmark="false")

    assert first["kpis"] == second["kpis"]
    assert calls["count"] == 1


def test_filters_reuse_the_cleaned_dataset(monkeypatch) -> None:
    calls = {"count": 0}
    real_clean = dataset_cache.load_and_clean_data

    def counted(frame):
        calls["count"] += 1
        return real_clean(frame)

    monkeypatch.setattr(dataset_cache, "load_and_clean_data", counted)

    analyze(retail_frame(), future_days=7, include_benchmark="false", store=["1"])
    analyze(retail_frame(), future_days=7, include_benchmark="false", store=["2"])

    assert calls["count"] == 1
