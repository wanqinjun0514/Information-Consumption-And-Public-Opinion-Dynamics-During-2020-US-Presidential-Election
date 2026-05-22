"""Project workflow helper."""
from __future__ import annotations

import pandas as pd


COLOR_SCALE_20260420 = [
    [0.0, "rgb(139, 26, 26)"],
    [0.25, "rgb(204, 102, 102)"],
    [0.5, "rgb(181, 216, 243)"],
    [0.75, "rgb(51, 102, 153)"],
    [1.0, "rgb(0, 51, 102)"],
]
MIDPOINT_20260420 = 0.352

COLOR_SCALE_LEGACY_PDF = [
    [0, "rgb(139, 26, 26)"],
    [0.2, "rgb(204, 102, 102)"],
    [0.3, "rgb(255, 153, 153)"],
    [0.3, "rgb(181, 216, 243)"],
    [0.8, "rgb(51, 102, 153)"],
    [1, "rgb(0, 51, 102)"],
]
MIDPOINT_LEGACY_PDF = 0.3

COLOR_RANGE = (0.0, 1.0)

CHOROPLETH_COLOR_SCALE = COLOR_SCALE_20260420
COLOR_MIDPOINT = MIDPOINT_20260420

BIN_LABELS = [
    "[-3,-2.5)",
    "[-2.5,-1.5)",
    "[-1.5,-0.5)",
    "[-0.5,0.5)",
    "[0.5,1.5)",
    "[1.5,2.5)",
    "[2.5,3]",
]
LEFT_BINS = BIN_LABELS[:3]
CENTER_BIN = BIN_LABELS[3]
RIGHT_BINS = BIN_LABELS[4:]


def prepare_locations_column(df: pd.DataFrame) -> pd.DataFrame:
    """Project workflow helper."""
    out = df.copy()
    loc = out["state_abbrev"].astype(str).str.strip()
    full = out["state_name"].astype(str).str.strip()
    plot_loc = loc.where(loc.str.len() == 2, full)
    plot_loc = plot_loc.replace({"nan": full, "": full})
    out["plot_loc"] = plot_loc
    return out


def score_to_bin_label(score: float) -> str | None:
    if pd.isna(score):
        return None
    edges = [-3, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3]
    for i in range(len(BIN_LABELS)):
        lo, hi = edges[i], edges[i + 1]
        if i < len(BIN_LABELS) - 1:
            if lo <= score < hi:
                return BIN_LABELS[i]
        else:
            if lo <= score <= hi:
                return BIN_LABELS[i]
    return None
