"""Project workflow helper."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
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

_sankey_dir = rp.DIR_02 / "04_monthly_crosstabs_sankey"
if str(_sankey_dir) not in sys.path:
    sys.path.insert(0, str(_sankey_dir))
from sankey_paths import MONTHS  # noqa: E402

_geo_dir = rp.DIR_08
if str(_geo_dir) not in sys.path:
    sys.path.insert(0, str(_geo_dir))
from geo_utils import build_id_to_state  # noqa: E402

from map_plot_utils import BIN_LABELS, CENTER_BIN, LEFT_BINS, RIGHT_BINS, score_to_bin_label

STATE_ABBREV = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "District of Columbia": "DC",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "Puerto Rico": "",
    "United States Virgin Islands": "",
}


def load_pooled_user_scores() -> pd.DataFrame:
    """Project workflow helper."""
    chunks = []
    for part in rp.GEO_MEDIA_PARTS:
        rating_dir = rp.media_rating_part_dir(part)
        for month in MONTHS:
            path = rating_dir / f"user_bias_scores_{month}.csv"
            if not path.is_file():
                continue
            df = pd.read_csv(path, dtype={"user_id": str})
            if {"user_id", "total_score", "appearance_count"}.issubset(df.columns):
                chunks.append(df[["user_id", "total_score", "appearance_count"]])
    if not chunks:
        raise FileNotFoundError(" user_bias_scores_*.csv done 02 media ")
    all_df = pd.concat(chunks, ignore_index=True)
    all_df["total_score"] = pd.to_numeric(all_df["total_score"], errors="coerce").fillna(0)
    all_df["appearance_count"] = pd.to_numeric(all_df["appearance_count"], errors="coerce").fillna(0)
    agg = all_df.groupby("user_id", as_index=False).agg(
        {"total_score": "sum", "appearance_count": "sum"}
    )
    agg["average_bias_points"] = np.where(
        agg["appearance_count"] > 0,
        agg["total_score"] / agg["appearance_count"],
        np.nan,
    )
    return agg


def build_state_user_bias_proportion() -> pd.DataFrame:
    id_to_state = build_id_to_state()
    users = load_pooled_user_scores()
    users["state"] = users["user_id"].map(id_to_state)
    users = users.dropna(subset=["state", "average_bias_points"])

    users["bin"] = users["average_bias_points"].map(score_to_bin_label)
    users = users.dropna(subset=["bin"])

    rows = []
    for state_name, grp in users.groupby("state"):
        n = len(grp)
        if n == 0:
            continue
        bin_props = grp["bin"].value_counts(normalize=True)
        row = {
            "state_name": state_name,
            "state_abbrev": STATE_ABBREV.get(state_name, ""),
        }
        for b in BIN_LABELS:
            row[b] = float(bin_props.get(b, 0.0))
        row["left_share"] = float(sum(row[b] for b in LEFT_BINS))
        row["center_share"] = float(row[CENTER_BIN])
        row["right_share"] = float(sum(row[b] for b in RIGHT_BINS))
        right = row["right_share"]
        row["left_right_ratio"] = row["left_share"] / right if right > 0 else np.nan
        rows.append(row)

    out = pd.DataFrame(rows)
    ratios = out["left_right_ratio"].replace([np.inf, -np.inf], np.nan).dropna()
    rmin, rmax = ratios.min(), ratios.max()
    if rmax > rmin:
        out["normalized_ratio"] = (out["left_right_ratio"] - rmin) / (rmax - rmin)
    else:
        out["normalized_ratio"] = 0.0
    out["normalized_ratio"] = out["normalized_ratio"].fillna(0.0)
    out = out.sort_values("normalized_ratio", ascending=True).reset_index(drop=True)
    return out


def main() -> None:
    df = build_state_user_bias_proportion()
    rp.ensure_dir(rp.STATE_USER_BIAS_PROPORTION_CSV.parent)
    df.to_csv(rp.STATE_USER_BIAS_PROPORTION_CSV, index=False, encoding="utf-8-sig")
    print(f"[done] write {len(df)} state_abbrev   {rp.STATE_USER_BIAS_PROPORTION_CSV}")


if __name__ == "__main__":
    main()
