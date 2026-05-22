"""Project workflow helper."""
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
from media_rating_utils import (
    MEDIA_DATA_PARTS,
    QUARTER_MONTHS,
    add_average_bias_points,
    classify_media_score,
)

BIAS_CATEGORIES = [
    "extreme_left",
    "left",
    "left_leaning",
    "center",
    "right_leaning",
    "right",
    "extreme_right",
]


def merge_quarterly_for_part(part: str) -> None:
    """Project workflow helper."""
    base = rp.media_rating_part_dir(part)
    for months in QUARTER_MONTHS:
        quarterly = pd.DataFrame()
        for month in months:
            fp = base / f"user_bias_scores_{month}.csv"
            if not fp.is_file():
                continue
            chunk = pd.read_csv(fp, dtype={"user_id": str})
            if "average_bias_points" not in chunk.columns:
                chunk = add_average_bias_points(chunk)
            chunk = chunk[["user_id", "total_score", "appearance_count", "average_bias_points"]]
            if quarterly.empty:
                quarterly = chunk
            else:
                quarterly = pd.concat([quarterly, chunk], ignore_index=True)
                quarterly = quarterly.groupby("user_id", as_index=False).agg(
                    {"total_score": "sum", "appearance_count": "sum"}
                )
                quarterly = add_average_bias_points(quarterly)
        if quarterly.empty:
            continue
        quarter_str = "_".join(months)
        out = base / f"quarterly_user_bias_scores_{quarter_str}.csv"
        quarterly.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"[quartermerge] {out}")


def classify_quarterly_users_for_part(part: str) -> None:
    base = rp.media_rating_part_dir(part)
    cohort_root = rp.ensure_dir(base / "user_bias_scores_by_quarter")
    for cat in BIAS_CATEGORIES:
        rp.ensure_dir(cohort_root / cat)

    for qfile in sorted(base.glob("quarterly_user_bias_scores_*.csv")):
        quarter = qfile.stem.replace("quarterly_user_bias_scores_", "")
        df = pd.read_csv(qfile, dtype={"user_id": str})
        if "average_bias_points" not in df.columns:
            df = add_average_bias_points(df)
        df["temp_category"] = df["average_bias_points"].apply(classify_media_score)
        for cat in BIAS_CATEGORIES:
            sub = df[df["temp_category"] == cat].drop(columns=["temp_category"])
            if sub.empty:
                continue
            out = cohort_root / cat / f"{quarter}_{cat}_user.csv"
            sub.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"[classify] {part} {quarter}")


def run_all(parts=MEDIA_DATA_PARTS) -> None:
    for part in parts:
        print(f"\n=== {part} ===")
        merge_quarterly_for_part(part)
        classify_quarterly_users_for_part(part)


if __name__ == "__main__":
    run_all()
