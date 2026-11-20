"""Shared FastAPI dependencies."""

from __future__ import annotations

import pandas as pd
from fastapi import File, HTTPException, UploadFile

from services import ingest
from services.ingest import UploadError, UploadTooLarge, read_tabular_upload


async def uploaded_frame(file: UploadFile = File(...)) -> pd.DataFrame:
    """Decode a CSV/XLSX upload, mapping file errors to HTTP errors."""
    if file.size and file.size > ingest.MAX_UPLOAD_BYTES:
        limit_mb = ingest.MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"File is larger than the {limit_mb} MB limit.")

    contents = await file.read()
    try:
        return read_tabular_upload(file.filename, contents)
    except UploadTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except UploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
