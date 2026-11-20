"""FastAPI routes for the forecast pipeline.

Thin routes: upload handling lives in ``api.dependencies``, filtering in
``utils.filters``, and business logic in ``services.forecast_service``.
"""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import uploaded_frame
from services.dataset_cache import get_cleaned_frame
from services.forecast_service import (
    get_future_forecast,
    run_forecast_pipeline,
    shape_fast_kpi_payload,
)
from utils.filters import filter_retail_frame
from utils.forecasting import MAX_FUTURE_DAYS

router = APIRouter(prefix="/forecast", tags=["forecast"])


def _clean_and_filter(
    df: pd.DataFrame,
    stores: list[str],
    categories: list[str],
    regions: list[str],
) -> pd.DataFrame:
    try:
        cleaned = get_cleaned_frame(df)
        return filter_retail_frame(cleaned, stores, categories, regions)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/run")
async def run_forecast(
    df: pd.DataFrame = Depends(uploaded_frame),
    horizon_days: int = Query(default=90, ge=30, le=365),
    store: list[str] = Query(default=[]),
    category: list[str] = Query(default=[]),
    region: list[str] = Query(default=[]),
):
    cleaned = _clean_and_filter(df, store, category, region)
    try:
        return run_forecast_pipeline(cleaned, horizon_days=horizon_days)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/future")
async def future_forecast(
    df: pd.DataFrame = Depends(uploaded_frame),
    future_days: int = Query(default=30, ge=1, le=MAX_FUTURE_DAYS),
    fast: bool = False,
    store: list[str] = Query(default=[]),
    category: list[str] = Query(default=[]),
    region: list[str] = Query(default=[]),
):
    cleaned = _clean_and_filter(df, store, category, region)
    try:
        return get_future_forecast(cleaned, future_days=future_days, fast=fast)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/kpis")
async def forecast_kpis(
    df: pd.DataFrame = Depends(uploaded_frame),
    store: list[str] = Query(default=[]),
    category: list[str] = Query(default=[]),
    region: list[str] = Query(default=[]),
):
    cleaned = _clean_and_filter(df, store, category, region)
    try:
        return shape_fast_kpi_payload(cleaned)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
