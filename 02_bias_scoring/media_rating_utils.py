"""Project workflow helper."""
from __future__ import annotations

import pandas as pd

MEDIA_DATA_PARTS = ("external_url", "twitter_url", "without_url")

QUARTER_MONTHS = [
    ["2019_12", "2020_01", "2020_02"],
    ["2020_03", "2020_04", "2020_05"],
    ["2020_06", "2020_07", "2020_08"],
    ["2020_09", "2020_10"],
    ["2020_11", "2020_12"],
    ["2021_01", "2021_02"],
]


def add_average_bias_points(df: pd.DataFrame) -> pd.DataFrame:
    """Project workflow helper."""
    out = df.copy()
    if "appearance_count" not in out.columns or "total_score" not in out.columns:
        raise ValueError("missing total_score  appearance_count column")
    denom = pd.to_numeric(out["appearance_count"], errors="coerce")
    numer = pd.to_numeric(out["total_score"], errors="coerce")
    out["average_bias_points"] = numer / denom.replace(0, pd.NA)
    return out


def classify_media_score(score) -> str | None:
    """Project workflow helper."""
    if pd.isna(score):
        return None
    try:
        s = float(score)
    except (TypeError, ValueError):
        return None
    if -3 <= s < -2.5:
        return "extreme_left"
    if -2.5 <= s < -1.5:
        return "left"
    if -1.5 <= s < -0.5:
        return "left_leaning"
    if -0.5 <= s <= 0.5:
        return "center"
    if 0.5 < s < 1.5:
        return "right_leaning"
    if 1.5 <= s < 2.5:
        return "right"
    if 2.5 <= s <= 3:
        return "extreme_right"
    return None
