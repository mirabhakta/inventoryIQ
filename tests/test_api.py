import io

import pandas as pd
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def sample_frame(periods: int = 120) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=periods, freq="D")
    rows = []
    for store, region in [(1, "West"), (2, "East")]:
        for index, current_date in enumerate(dates):
            sales = 100.0 if index < periods - 28 else 50.0
            rows.append(
                {
                    "Order Date": current_date,
                    "Store": store,
                    "Product": "Mug",
                    "Category": "Kitchen",
                    "Region": region,
                    "Sales": sales,
                }
            )
    return pd.DataFrame(rows)


def csv_upload(frame: pd.DataFrame, filename: str = "sales.csv") -> dict:
    return {"file": (filename, frame.to_csv(index=False).encode("utf-8"), "text/csv")}


def xlsx_upload(frame: pd.DataFrame, filename: str = "sales.xlsx") -> dict:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)
    return {
        "file": (
            filename,
            buffer.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def test_alerts_accept_xlsx_uploads() -> None:
    response = client.post("/alerts/run", files=xlsx_upload(sample_frame(periods=40)))

    assert response.status_code == 200
    assert set(response.json()) == {"alerts", "total"}


def test_store_filter_is_applied_server_side() -> None:
    response = client.post(
        "/alerts/run",
        files=csv_upload(sample_frame()),
        params={"store": ["2"]},
    )

    assert response.status_code == 200
    alerts = response.json()["alerts"]
    assert alerts
    assert {alert["store_id"] for alert in alerts} == {2}


def test_region_filter_is_applied_server_side() -> None:
    response = client.post(
        "/alerts/run",
        files=csv_upload(sample_frame()),
        params={"region": ["West"]},
    )

    assert response.status_code == 200
    alerts = response.json()["alerts"]
    assert alerts
    assert {alert["store_id"] for alert in alerts} == {1}


def test_kpi_total_respects_the_store_filter() -> None:
    unfiltered = client.post("/forecast/kpis", files=csv_upload(sample_frame()))
    filtered = client.post(
        "/forecast/kpis",
        files=csv_upload(sample_frame()),
        params={"store": ["1"]},
    )

    assert unfiltered.status_code == 200
    assert filtered.status_code == 200
    assert filtered.json()["total_sales"] == 10600.0
    assert filtered.json()["total_sales"] < unfiltered.json()["total_sales"]


def test_unsupported_file_type_returns_400() -> None:
    response = client.post(
        "/alerts/run",
        files={"file": ("sales.txt", b"Order Date,Sales\n2024-01-01,10\n", "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_oversized_upload_returns_413(monkeypatch) -> None:
    monkeypatch.setattr("services.ingest.MAX_UPLOAD_BYTES", 10)

    response = client.post(
        "/alerts/run",
        files={"file": ("sales.csv", b"0123456789A", "text/csv")},
    )

    assert response.status_code == 413


def test_missing_sales_column_returns_422() -> None:
    frame = pd.DataFrame(
        {"Order Date": ["2024-01-01"], "Product": ["Mug"], "Category": ["Kitchen"]}
    )

    response = client.post("/alerts/run", files=csv_upload(frame))

    assert response.status_code == 422
    assert "sales" in response.json()["detail"]


def test_empty_filter_result_returns_422() -> None:
    response = client.post(
        "/alerts/run",
        files=csv_upload(sample_frame()),
        params={"store": ["999"]},
    )

    assert response.status_code == 422
    assert "No rows match" in response.json()["detail"]


def test_future_forecast_returns_records_and_method() -> None:
    response = client.post(
        "/forecast/future",
        files=csv_upload(sample_frame()),
        params={"future_days": 14},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["future_days"] == 14
    assert body["method"] in {"lightgbm_global_lag", "simple_last_value_future"}
    assert len(body["forecast_records"]) == 14 * 2


def test_future_forecast_rejects_horizon_over_the_cap() -> None:
    response = client.post(
        "/forecast/future",
        files=csv_upload(sample_frame()),
        params={"future_days": 181},
    )

    assert response.status_code == 422


def test_forecast_benchmark_runs_with_filters() -> None:
    response = client.post(
        "/forecast/run",
        files=csv_upload(sample_frame()),
        params={"horizon_days": 30, "region": ["West"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert "winner" in body
    assert body["comparison_table"]


def test_forecast_benchmark_rejects_large_uploads(monkeypatch) -> None:
    monkeypatch.setattr("api.forecast_routes.MAX_BENCHMARK_ROWS", 10)

    response = client.post("/forecast/run", files=csv_upload(sample_frame()))

    assert response.status_code == 422
    assert "limited to" in response.json()["detail"]

SUMMARY_PAYLOAD = {
    "trend": "increasing",
    "winner_model": "lightgbm_global_lag",
    "mae": 12.3,
    "total_sales": 673603.68,
    "alert_count": 7,
    "top_product": "Aurora Desk Lamp",
    "top_category": "Home",
}


def test_summary_requires_configuration(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.post("/summary", json=SUMMARY_PAYLOAD)

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_summary_returns_generated_text(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.summary_routes.generate_summary",
        lambda payload: "Sales are increasing and the top product leads demand.",
    )

    response = client.post("/summary", json=SUMMARY_PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {
        "summary": "Sales are increasing and the top product leads demand."
    }


def test_summary_rejects_overlong_fields() -> None:
    response = client.post(
        "/summary",
        json={**SUMMARY_PAYLOAD, "top_product": "A" * 121},
    )

    assert response.status_code == 422
