# InventoryIQ — Backend API

FastAPI service for schema mapping, demand forecasting, alert detection, and
AI-written summaries.

## Running Locally

```bash
git clone https://github.com/mirabhakta/inventoryIQ.git
cd inventoryIQ
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# add GEMINI_API_KEY to your .env locally (see .env.example)
uvicorn main:app --reload
# interactive docs at http://localhost:8000/docs
```

A ready-to-upload example is available at `data/sample_sales.csv`.

## Conventions

- File endpoints accept `multipart/form-data` with a field named `file`.
- Supported formats: `.csv` and `.xlsx`. Limits: **10 MB** and **50,000 rows**.
- Filters are repeatable query parameters: `store`, `category`, `region`.
- Error responses use FastAPI's `{"detail": "..."}` shape:
  - `400` — unsupported type, empty file, or unreadable content
  - `413` — file too large
  - `422` — invalid data, no rows match the filters, or an out-of-range horizon
  - `503` — the AI summary is not configured or Gemini is unavailable

## Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/` | Service status |
| POST | `/analyze` | Complete dashboard payload for the current filters |
| POST | `/forecast/run` | Trains all four models and returns the benchmark |
| POST | `/forecast/future` | Returns per-series future forecast records |
| POST | `/forecast/kpis` | Fast KPI summary without model training |
| POST | `/alerts/run` | Runs all three alert detectors |
| POST | `/summary` | Generates a Gemini summary from dashboard metrics |

---

## POST `/analyze`

The dashboard's primary endpoint. One request returns filter options, KPIs,
aggregates, a monthly forecast, alerts, and an optional benchmark.

**Query parameters**

| Name | Type | Default | Notes |
|---|---|---|---|
| `future_days` | int | `90` | 1–180 |
| `include_benchmark` | bool | `true` | Set `false` on filter changes |
| `store` | string[] | `[]` | Repeat for multiple stores |
| `category` | string[] | `[]` | |
| `region` | string[] | `[]` | Requires a region column |

**Response (abridged)**

```json
{
  "meta": {
    "row_count": 600,
    "total_row_count": 1800,
    "date_range": { "start": "2024-01-01", "end": "2024-04-29" },
    "stores": [1, 2, 3],
    "categories": ["Accessories", "Electronics", "Home", "Kitchen"],
    "regions": ["Central", "East", "West"],
    "column_mapping": { "date": "Order Date", "sales": "Sales" },
    "optional_fields": { "profit": "active", "region": "active" },
    "aggregation_notes": []
  },
  "kpis": {
    "total_sales": 224534.56,
    "projected_sales": 180321.4,
    "forecast_direction": "flat",
    "forecast_method": "lightgbm_global_lag",
    "winner_model": "lightgbm_global_lag",
    "mae": 38.795,
    "mase": 1.583,
    "alert_count": 2,
    "row_count": 600,
    "top_product": "Vertex Keyboard",
    "top_category": "Home"
  },
  "history": { "monthly": [{ "month": "2024-01", "total_sales": 55800.0 }] },
  "products": {
    "top": [{ "product_id": 4, "product": "Vertex Keyboard", "total_sales": 69000.0 }],
    "bottom": []
  },
  "stores": [{ "store_id": 1, "total_sales": 224534.56 }],
  "categories": [{ "category": "Home", "total_sales": 80000.0 }],
  "forecast": {
    "method": "lightgbm_global_lag",
    "future_days": 90,
    "monthly": [{ "month": "2024-05", "prediction": 60000.0 }],
    "total": 180321.4,
    "direction": "flat"
  },
  "benchmark": {
    "winner": "lightgbm_global_lag",
    "metrics": { "mae": 38.795, "rmse": 167.376, "mase": 1.583 },
    "table": [{ "method_name": "lightgbm_global_lag", "mae": 38.795, "rmse": 167.376, "mase": 1.583 }]
  },
  "alerts": { "items": [], "total": 0 }
}
```

`meta.stores`, `categories`, `regions`, and `date_range` describe the **full**
dataset so the sidebar does not collapse to the current selection.

The forecast is returned as **monthly totals**, not one record per series per
day. Use `/forecast/future` when you need the raw records.

---

## POST `/forecast/run`

Trains naive, rolling-average, ridge, and LightGBM models on a time-based split
and returns the winner by MASE, then MAE, then RMSE.

```json
{
  "winner": "lightgbm_global_lag",
  "metrics": { "mae": 38.795, "rmse": 167.376, "mase": 1.583 },
  "comparison_table": [
    { "method_name": "lightgbm_global_lag", "mae": 38.795, "rmse": 167.376, "mase": 1.583 },
    { "method_name": "feature_based_regression", "mae": 40.12, "rmse": 150.2, "mase": 1.64 },
    { "method_name": "rolling_average_3", "mae": 52.3, "rmse": 180.1, "mase": 2.1 },
    { "method_name": "naive_last_value", "mae": 61.7, "rmse": 205.4, "mase": 2.5 }
  ]
}
```

Query parameters: `horizon_days` (30–365, default 90) plus the standard filters.

---

## POST `/forecast/future`

Returns `future_days` of daily records per store/item series.

```json
{
  "method": "lightgbm_global_lag",
  "future_days": 30,
  "forecast_records": [
    {
      "date": "2024-04-30T00:00:00",
      "store": 1,
      "item": 1,
      "actual": null,
      "prediction": 484.46,
      "residual": null,
      "method_name": "lightgbm_global_lag"
    }
  ]
}
```

`future_days` is capped at **180**. The method is `lightgbm_global_lag` when the
history supports the lag features; otherwise the response reports
`simple_last_value_future`.

---

## POST `/forecast/kpis`

Fast KPI cards without training a model:

```json
{
  "total_sales": 673603.68,
  "forecast_direction": "flat",
  "winner_model": "fast_upload_summary",
  "mae": null
}
```

Use `/forecast/run` or `/analyze` with `include_benchmark=true` for model
accuracy.

---

## POST `/alerts/run`

Runs anomaly, demand-decline, and margin detectors per store/product.

Query parameters: `anomaly_std` (default 2.0), `decline_pct` (default 0.20),
`margin_floor` (default 0.0), plus the standard filters.

```json
{
  "alerts": [
    {
      "store_id": 2,
      "product_id": 4,
      "product_name": "Vertex Keyboard",
      "alert_type": "Sales Anomaly",
      "direction": "spike",
      "severity": 77.17,
      "priority": 3,
      "metric": "Sales of 4,504 is 77.2 std devs above the 90-day mean of 553"
    }
  ],
  "total": 1
}
```

`priority` is `1` for Low Margin, `2` for Demand Decline, and `3` for Sales
Anomaly. Alerts are sorted by priority, then severity descending. `direction` is
one of `spike`, `drop`, `decline`, or `margin`.

---

## POST `/summary`

Generates a 2–3 sentence summary from already-computed metrics. The Gemini call
happens only when this endpoint is hit.

Request:

```json
{
  "trend": "flat",
  "winner_model": "lightgbm_global_lag",
  "mae": 38.795,
  "total_sales": 673603.68,
  "alert_count": 7,
  "top_product": "Vertex Keyboard",
  "top_category": "Home"
}
```

Response:

```json
{ "summary": "Sales are holding steady this period. Vertex Keyboard is the top performer..." }
```

Requires `GEMINI_API_KEY`. Without it, the endpoint returns `503` with
`GEMINI_API_KEY is not configured.` and the dashboard shows a configuration
message. `GEMINI_MODEL` can override the default (`gemini-3.8-flash`).

---

## Limitations

- The hosted demo is sized for a single-instance deployment: 10 MB / 50k rows.
- Forecasting is capped at 180 days.
- No authentication or rate limiting; this is a portfolio demo, not a production
  multi-tenant service.
- Model training runs per request. The dashboard skips the benchmark on filter
  changes to keep interactions fast.
