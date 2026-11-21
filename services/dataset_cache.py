"""Caches for parsed/cleaned datasets and computed dashboard payloads.

Keys are derived from the uploaded bytes, so re-uploading the same file while
changing filters reuses the cleaned frame and, for identical requests, the
computed payload.
"""

from __future__ import annotations

import copy

import pandas as pd

from services.cache import TTLCache
from utils.processor import load_and_clean_data

# A cleaned dashboard frame can be large at the upload limit, so keep only one.
# Filter changes reuse the same upload; another file simply evicts the previous.
CLEANED_DATASETS: TTLCache[pd.DataFrame] = TTLCache(maxsize=1, ttl_seconds=900)
ANALYSIS_RESULTS: TTLCache[dict] = TTLCache(maxsize=16, ttl_seconds=900)


def get_cleaned_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return a cleaned frame, reusing the cache when the upload hash matches."""
    key = df.attrs.get("cache_key")
    if not key:
        return load_and_clean_data(df)

    cached = CLEANED_DATASETS.get(key)
    if cached is not None:
        return cached.copy()

    cleaned = load_and_clean_data(df)
    CLEANED_DATASETS.set(key, cleaned)
    return cleaned


def analysis_cache_key(
    df: pd.DataFrame,
    future_days: int,
    include_benchmark: bool,
    stores: list[str],
    categories: list[str],
    regions: list[str],
) -> str | None:
    """Build a stable key for one file + filter + horizon combination."""
    upload_key = df.attrs.get("cache_key")
    if not upload_key:
        return None

    return "|".join(
        [
            upload_key,
            str(int(future_days)),
            "benchmark" if include_benchmark else "fast",
            ",".join(sorted(stores)),
            ",".join(sorted(categories)),
            ",".join(sorted(regions)),
        ]
    )


def get_cached_analysis(key: str) -> dict | None:
    value = ANALYSIS_RESULTS.get(key)
    return copy.deepcopy(value) if value is not None else None


def cache_analysis(key: str, result: dict) -> None:
    ANALYSIS_RESULTS.set(key, result)


def reset_caches() -> None:
    """Clear both caches; used by tests and operational resets."""
    CLEANED_DATASETS.clear()
    ANALYSIS_RESULTS.clear()
