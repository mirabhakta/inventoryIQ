"""FastAPI routes for the alert engine.

Thin routes: upload handling lives in ``api.dependencies``, filtering in
``utils.filters``, and detection in ``models.alerter``.
"""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import uploaded_frame
from models.alerter import run_all_alerts
from services.dataset_cache import get_cleaned_frame
from utils.filters import filter_retail_frame

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/run")
async def run_alerts(
    df: pd.DataFrame = Depends(uploaded_frame),
    anomaly_std: float = Query(default=2.0, gt=0, le=10),
    decline_pct: float = Query(default=0.20, ge=0, le=1),
    margin_floor: float = Query(default=0.0, ge=-1, le=1),
    store: list[str] = Query(default=[]),
    category: list[str] = Query(default=[]),
    region: list[str] = Query(default=[]),
):
    try:
        cleaned = get_cleaned_frame(df)
        cleaned = filter_retail_frame(cleaned, store, category, region)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    thresholds = {
        "anomaly_std": anomaly_std,
        "decline_pct": decline_pct,
        "margin_floor": margin_floor,
    }

    try:
        alerts_df = run_all_alerts(cleaned, thresholds=thresholds)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if alerts_df.empty:
        return {"alerts": [], "total": 0}

    return {
        "alerts": alerts_df.to_dict(orient="records"),
        "total": len(alerts_df),
    }
