# -*- coding: utf-8 -*-
"""Project workflow helper."""
from __future__ import annotations

import sys
from pathlib import Path

import joypy
import matplotlib.pyplot as plt
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

IN_CSV = rp.PLOT_DATA_ALL_SOURCES_RAW_CSV
OUT_DIR = rp.DIR_06_RIDGE_PLOTS

APPEAR_THRESHOLD = 5
XLIM = (0, 6)

BIAS_ORDER = [
    "extreme_right",
    "right",
    "right_leaning",
    "center",
    "left_leaning",
    "left",
    "extreme_left",
]

BIAS_ABBR = {
    "extreme_left": "EL",
    "left": "L",
    "left_leaning": "LL",
    "center": "C",
    "right_leaning": "RL",
    "right": "R",
    "extreme_right": "ER",
}

NODE_COLOR_MAP = {
    "extreme_left": (0 / 255, 51 / 255, 102 / 255),
    "left": (51 / 255, 102 / 255, 153 / 255),
    "left_leaning": (181 / 255, 216 / 255, 243 / 255),
    "center": (240 / 255, 230 / 255, 140 / 255),
    "right_leaning": (255 / 255, 153 / 255, 153 / 255),
    "right": (204 / 255, 102 / 255, 102 / 255),
    "extreme_right": (139 / 255, 26 / 255, 26 / 255),
}


def plot_ridgeline_total():
    if not IN_CSV.exists():
        raise FileNotFoundError(f" CSV {IN_CSV} row 02_generatecsv__data.py")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(IN_CSV)
    dff = df[df["source"] == "total"].copy()
    if dff.empty:
        raise ValueError("plot_data  source='total' ")

    dff["appear_count"] = pd.to_numeric(dff["appear_count"], errors="coerce")
    dff["average_info_openmindness"] = pd.to_numeric(dff["average_info_openmindness"], errors="coerce")

    dff = dff[dff["appear_count"].fillna(-np.inf) >= APPEAR_THRESHOLD]
    dff = dff[np.isfinite(dff["average_info_openmindness"])]
    dff = dff[
        (dff["average_info_openmindness"] >= XLIM[0])
        & (dff["average_info_openmindness"] <= XLIM[1])
    ]

    present = [b for b in BIAS_ORDER if b in set(dff["bias"].unique())]
    if not present:
        present = sorted(dff["bias"].unique().tolist())

    total_n = len(dff)
    data, labels, plot_colors = [], [], []

    for b in present:
        all_vals = dff.loc[dff["bias"] == b, "average_info_openmindness"].dropna().values
        if len(all_vals) == 0:
            continue
        total_count = len(all_vals)
        zero_count = int(np.sum(all_vals == 0))
        zero_pct = (zero_count / total_count * 100) if total_count > 0 else 0
        non_zero_vals = all_vals[all_vals > 0]
        if len(non_zero_vals) == 0:
            continue
        data.append(non_zero_vals)
        labels.append(
            f"{BIAS_ABBR.get(b, b)} (Total={total_count:,})\n"
            f"0 values: {zero_count:,} ({zero_pct:.1f}%)"
        )
        plot_colors.append(NODE_COLOR_MAP.get(b, (0.5, 0.5, 0.5)))

    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["figure.subplot.left"] = 0.15

    fig, axes = joypy.joyplot(
        data,
        labels=labels,
        grid="y",
        linewidth=1,
        figsize=(12, 8),
        color=plot_colors,
        x_range=XLIM,
    )
    axes[-1].set_xlabel("Openmindness (>0)")
    fig.suptitle(
        f"Openmindness Ridgeline (Total) | appear_count >= {APPEAR_THRESHOLD} | Excl. Zeros\n"
        f"Total samples: {total_n:,}",
        fontsize=14,
    )

    save_path = OUT_DIR / f"ridgeline_total_appear_ge_{APPEAR_THRESHOLD}_no_zeros.png"
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[done] save: {save_path}")


if __name__ == "__main__":
    plot_ridgeline_total()
