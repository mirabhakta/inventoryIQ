"""Single-call dashboard analysis route."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import uploaded_frame
from services.analysis_service import analyze_retail_data
from utils.filters import filter_retail_frame
from utils.forecasting import MAX_FUTURE_DAYS
from utils.processor import load_and_clean_data

router = APIRouter(tags=["analysis"])


@router.post("/analyze")
async def analyze_dataset(
    df: pd.DataFrame = Depends(uploaded_frame),
    future_days: int = Query(default=90, ge=1, le=MAX_FUTURE_DAYS),
    include_benchmark: bool = True,
    store: list[str] = Query(default=[]),
    category: list[str] = Query(default=[]),
    region: list[str] = Query(default=[]),
):
    try:
        cleaned = load_and_clean_data(df)
        filtered = filter_retail_frame(cleaned, store, category, region)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        return analyze_retail_data(
            cleaned,
            filtered,
            future_days=future_days,
            include_benchmark=include_benchmark,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
