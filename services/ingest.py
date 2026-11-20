"""Read uploaded retail files into DataFrames.

The browser sends the raw file, so the API owns decoding, format support, and
resource limits. Keeping this in one place means every endpoint accepts the
same files and returns the same error messages.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_UPLOAD_ROWS = 200_000

SUPPORTED_SUFFIXES = {".csv", ".xlsx"}


class UploadError(ValueError):
    """The uploaded file cannot be used as a retail table."""


class UploadTooLarge(UploadError):
    """The uploaded file exceeds the size or row limit."""


def _read_csv(contents: bytes) -> pd.DataFrame:
    last_error: UnicodeDecodeError | None = None

    # utf-8-sig handles Excel's BOM; cp1252 covers Windows exports; latin-1 is
    # the final catch-all so an odd byte does not reject an otherwise usable file.
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(contents), encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.EmptyDataError as exc:
            raise UploadError("The uploaded CSV is empty.") from exc
        except pd.errors.ParserError as exc:
            raise UploadError(
                "The CSV could not be parsed. Check the delimiter and quoting."
            ) from exc

    raise UploadError("The CSV encoding could not be read. Save it as UTF-8.") from last_error


def _read_excel(contents: bytes) -> pd.DataFrame:
    try:
        return pd.read_excel(io.BytesIO(contents), engine="openpyxl")
    except Exception as exc:  # openpyxl raises several format-specific errors
        raise UploadError(
            "The Excel file could not be read. Save it as .xlsx or .csv and try again."
        ) from exc


def read_tabular_upload(filename: str | None, contents: bytes) -> pd.DataFrame:
    """
    Decode an uploaded CSV or XLSX file and enforce the demo resource limits.

    Raises:
        UploadError: unsupported type, empty, unreadable, or too many rows.
        UploadTooLarge: larger than ``MAX_UPLOAD_BYTES``.
    """
    if not contents:
        raise UploadError("The uploaded file is empty.")

    if len(contents) > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        actual_mb = len(contents) / (1024 * 1024)
        raise UploadTooLarge(
            f"This file is {actual_mb:.1f} MB, but the demo supports up to {limit_mb} MB "
            "per upload. Filter to a recent date range or a subset of stores/products "
            "and try again."
        )

    suffix = Path(filename or "").suffix.lower()
    if suffix == ".xls":
        raise UploadError(
            "Legacy .xls files are not supported. Save as .xlsx or .csv and try again."
        )
    if suffix not in SUPPORTED_SUFFIXES:
        raise UploadError("Unsupported file type. Upload a .csv or .xlsx file.")

    frame = _read_csv(contents) if suffix == ".csv" else _read_excel(contents)

    if frame.empty or len(frame.columns) == 0:
        raise UploadError("The uploaded file has no rows. Add data and try again.")

    if len(frame) > MAX_UPLOAD_ROWS:
        raise UploadTooLarge(
            f"This file has {len(frame):,} rows, but the demo supports up to "
            f"{MAX_UPLOAD_ROWS:,} rows per upload. Filter to a recent date range or "
            "a subset of stores/products and try again."
        )

    return frame
