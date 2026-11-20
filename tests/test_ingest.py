import io

import pandas as pd
import pytest

from services import ingest
from services.ingest import (
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_ROWS,
    UploadError,
    UploadTooLarge,
    read_tabular_upload,
)


def csv_bytes(text: str, encoding: str = "utf-8") -> bytes:
    return text.encode(encoding)


def test_reads_csv_with_quoted_commas() -> None:
    contents = csv_bytes(
        'Order Date,Sales,Product\n2024-01-01,10,"Shirt, Blue"\n2024-01-02,20,Hat\n'
    )

    frame = read_tabular_upload("sales.csv", contents)

    assert frame.loc[0, "Product"] == "Shirt, Blue"
    assert frame.loc[0, "Sales"] == 10


def test_reads_utf8_bom_csv() -> None:
    contents = csv_bytes("Order Date,Sales\n2024-01-01,10\n", encoding="utf-8-sig")

    frame = read_tabular_upload("sales.csv", contents)

    assert list(frame.columns) == ["Order Date", "Sales"]
    assert frame.loc[0, "Sales"] == 10


def test_reads_cp1252_csv() -> None:
    contents = csv_bytes("Order Date,Sales,Product\n2024-01-01,10,Café\n", encoding="cp1252")

    frame = read_tabular_upload("sales.csv", contents)

    assert frame.loc[0, "Product"] == "Café"


def test_reads_xlsx() -> None:
    frame = pd.DataFrame(
        {"Order Date": ["2024-01-01"], "Sales": [10.0], "Product": ["Shirt"]}
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)

    parsed = read_tabular_upload("sales.xlsx", buffer.getvalue())

    assert list(parsed.columns) == ["Order Date", "Sales", "Product"]
    assert parsed.loc[0, "Sales"] == 10.0


def test_rejects_unsupported_extension() -> None:
    with pytest.raises(UploadError, match="Unsupported file type"):
        read_tabular_upload("sales.txt", b"nope")


def test_rejects_legacy_xls_with_a_clear_message() -> None:
    with pytest.raises(UploadError, match="Save as .xlsx or .csv"):
        read_tabular_upload("sales.xls", b"nope")


def test_rejects_empty_file() -> None:
    with pytest.raises(UploadError, match="empty"):
        read_tabular_upload("sales.csv", b"")


def test_rejects_files_over_the_size_limit() -> None:
    with pytest.raises(UploadTooLarge, match="10 MB"):
        read_tabular_upload("sales.csv", b"0" * (MAX_UPLOAD_BYTES + 1))


def test_rejects_files_over_the_row_limit(monkeypatch) -> None:
    monkeypatch.setattr(ingest, "MAX_UPLOAD_ROWS", 2)
    contents = csv_bytes("Order Date,Sales\n2024-01-01,1\n2024-01-02,2\n2024-01-03,3\n")

    with pytest.raises(UploadTooLarge, match="3 rows.*2 rows.*Filter"):
        read_tabular_upload("sales.csv", contents)


def test_limits_are_reported_in_megabytes_and_rows() -> None:
    assert MAX_UPLOAD_BYTES == 10 * 1024 * 1024
    assert MAX_UPLOAD_ROWS == 200_000
