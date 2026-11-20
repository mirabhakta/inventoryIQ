"""Single-call dashboard analysis route."""

from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import uploaded_frame
from services.analysis_service import analyze_retail_data
from services.dataset_cache import (
    analysis_cache_key,
    cache_analysis,
    get_cached_analysis,
    get_cleaned_frame,
)
from utils.filters import filter_retail_frame
from utils.forecasting import MAX_FUTURE_DAYS

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
    cache_key = analysis_cache_key(
        df,
        future_days=future_days,
        include_benchmark=include_benchmark,
        stores=store,
        categories=category,
        regions=region,
    )
    if cache_key:
        cached = get_cached_analysis(cache_key)
        if cached is not None:
            return cached

    try:
        cleaned = get_cleaned_frame(df)
        filtered = filter_retail_frame(cleaned, store, category, region)
        result = analyze_retail_data(
            cleaned,
            filtered,
            future_days=future_days,
            include_benchmark=include_benchmark,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if cache_key:
        cache_analysis(cache_key, result)
    return result
