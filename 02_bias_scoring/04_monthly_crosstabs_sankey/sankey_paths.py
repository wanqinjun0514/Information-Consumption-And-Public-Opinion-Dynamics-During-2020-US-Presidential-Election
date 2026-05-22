"""Project workflow helper."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_rp = Path(__file__).resolve()
for _ in range(8):
    if (_rp / "repo_paths.py").exists():
        if str(_rp) not in sys.path:
            sys.path.insert(0, str(_rp))
        break
    _rp = _rp.parent
else:
    raise RuntimeError("Repository root not found; repo_paths.py is missing.")

import repo_paths as rp

_SANKEY_DIR = Path(__file__).resolve().parent
if str(_SANKEY_DIR) not in sys.path:
    sys.path.insert(0, str(_SANKEY_DIR))

MONTHS = [
    "2019_12", "2020_01", "2020_02", "2020_03", "2020_04", "2020_05",
    "2020_06", "2020_07", "2020_08", "2020_09", "2020_10", "2020_11",
    "2020_12", "2021_01", "2021_02",
]

QUARTER_MONTHS = [
    ["2019_12", "2020_01", "2020_02"],
    ["2020_03", "2020_04", "2020_05"],
    ["2020_06", "2020_07", "2020_08"],
    ["2020_09", "2020_10"],
    ["2020_11", "2020_12"],
    ["2021_01", "2021_02"],
]

QUARTER_LABELS = ["_".join(m) for m in QUARTER_MONTHS]

MEDIA_DATA_PARTS = ("external_url", "twitter_url", "without_url")
POLITICIAN_DATA_PARTS = ("external_url", "twitter_url", "without_url")


def month_pairs():
    return list(zip(MONTHS[:-1], MONTHS[1:]))


def adjacent_quarter_pairs():
    return list(zip(QUARTER_LABELS[:-1], QUARTER_LABELS[1:]))


def media_rating_dir(part: str) -> Path:
    return rp.DIR_02_MEDIA_RATING_ROOT / f"{part}-rating"


def media_monthly_sankey_dir(part: str, *sub: str) -> Path:
    return media_rating_dir(part) / "sankey_plot" / "every_month" / Path(*sub)


def media_quarterly_file(part: str, quarter_label: str) -> Path:
    return media_rating_dir(part) / f"quarterly_user_bias_scores_{quarter_label}.csv"


def media_new_user_sankey_dir(part: str, *sub: str) -> Path:
    return media_rating_dir(part) / "sankey_plot" / "every_quarter_with_new_users" / Path(*sub)


def politician_rating_dir(part: str) -> Path:
    return rp.DIR_02_POLITICIAN_RATING_ROOT / f"{part}-rating"


def politician_monthly_dir(part: str) -> Path:
    return politician_rating_dir(part) / "monthly_users_bias"


def politician_monthly_sankey_dir(part: str, *sub: str) -> Path:
    return politician_rating_dir(part) / "sankey_plot" / "every_month" / Path(*sub)


def politician_quarterly_file(part: str, quarter_label: str) -> Path:
    return (
        politician_rating_dir(part)
        / "quaterly_users_bias"
        / f"quarterly_user_bias_scores_{quarter_label}.csv"
    )


def politician_total_quarter_dir() -> Path:
    return rp.DIR_02_POLITICIAN_RATING_ROOT / "total_url-rating" / "user_bias_scores_by_quarter"


def politician_total_quarterly_file(quarter_label: str) -> Path:
    return politician_total_quarter_dir() / f"quarterly_user_bias_scores_{quarter_label}.csv"


def politician_new_user_sankey_dir(part: str, *sub: str) -> Path:
    return politician_rating_dir(part) / "sankey_plot" / "every_quarter_with_new_users" / Path(*sub)


def read_media_monthly_user_bias(file_path: Path) -> pd.DataFrame:
    """Project workflow helper."""
    df = pd.read_csv(
        file_path,
        dtype={"user_id": "str", "total_score": "float64", "appearance_count": "int64"},
    )
    if "average_bias_points" in df.columns:
        return df[["user_id", "average_bias_points"]].astype({"average_bias_points": "float64"})
    needed = {"user_id", "total_score", "appearance_count"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"{file_path} missingcolumn: {missing}")
    df = df[list(needed)].copy()
    df["average_bias_points"] = df["total_score"] / df["appearance_count"]
    return df[["user_id", "average_bias_points"]]
