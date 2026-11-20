import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.processor import load_and_clean_data


OPTIONAL_FIELDS = ["profit", "region", "transaction_count"]


def print_test_result(name: str, clean_df: pd.DataFrame) -> None:
    print("\n" + "=" * 60)
    print(f"DATASET: {name}")
    print("=" * 60)

    print(f"Rows/Columns: {clean_df.shape[0]} rows, {clean_df.shape[1]} columns")

    print("\nOutput columns:")
    for column in clean_df.columns:
        print(f"- {column}")

    present = [field for field in OPTIONAL_FIELDS if field in clean_df.columns]
    missing = [field for field in OPTIONAL_FIELDS if field not in clean_df.columns]

    print("\nOptional fields present:")
    print(present if present else "None")

    print("\nOptional fields missing:")
    print(missing if missing else "None")

    print("\nPreview:")
    print(clean_df.head(3))


def export_temp_preview(file_name: str, clean_df: pd.DataFrame) -> None:
    output_path = PROJECT_ROOT / "data" / file_name
    try:
        clean_df.to_csv(output_path, index=False)
    except PermissionError:
        print(f"\nCould not update {output_path}; close the file and rerun the test.")
        return

    print(f"\nFull cleaned output saved to: {output_path}")


def main() -> None:
    sample_raw = pd.read_csv(PROJECT_ROOT / "data" / "sample_sales.csv")
    sample_clean = load_and_clean_data(sample_raw)
    print_test_result("Bundled demo dataset", sample_clean)
    export_temp_preview("temp_sample_clean_preview.csv", sample_clean)

    walmart_path = PROJECT_ROOT / "data" / "walmart.xlsx"
    if not walmart_path.exists():
        print("\nSkipping Retail Orders test: add data/walmart.xlsx to run it locally.")
        return

    walmart_raw = pd.read_excel(walmart_path)
    walmart_clean = load_and_clean_data(walmart_raw)
    print_test_result("Retail Orders / Walmart", walmart_clean)
    export_temp_preview("temp_walmart_clean_preview.csv", walmart_clean)


if __name__ == "__main__":
    main()
