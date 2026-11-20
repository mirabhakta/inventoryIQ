import pandas as pd


def compute_trend(df: pd.DataFrame) -> str:
    """
    Determines trend direction: increasing, flat, or declining
    based on recent sales.
    """

    # Sort by date
    df = df.sort_values("date")

    # Take last N points (recent window)
    recent = df["sales"].tail(7)

    # If not enough data
    if len(recent) < 2:
        return "flat"

    # Simple slope: last - first
    slope = recent.iloc[-1] - recent.iloc[0]

    # Thresholds (avoid noise)
    if slope > 0:
        return "increasing"
    elif slope < 0:
        return "declining"
    else:
        return "flat"