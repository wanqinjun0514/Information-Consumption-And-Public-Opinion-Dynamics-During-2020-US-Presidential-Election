import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import LogNorm

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


def merge_monthly_consumption_matrices_from_three_sources():
    source_folders = [
        rp.MEDIA_EXTERNAL_INFORMATION_CONSUME,
        rp.MEDIA_TWITTER_INFORMATION_CONSUME,
        rp.MEDIA_WITHOUT_INFORMATION_CONSUME,
    ]
    months = ["2019_12"] + [f"2020_{str(m).zfill(2)}" for m in range(1, 13)] + ["2021_01", "2021_02"]

    std_mapping = {
        "extreme bias left": "Extreme Left",
        "extreme left": "Extreme Left",
        "left": "Left",
        "left leaning": "Left Leaning",
        "center": "Center",
        "right leaning": "Right Leaning",
        "right": "Right",
        "extreme bias right": "Extreme Right",
        "extreme right": "Extreme Right",
    }

    ordered_categories = [
        "Extreme Left",
        "Left",
        "Left Leaning",
        "Center",
        "Right Leaning",
        "Right",
        "Extreme Right",
    ]

    total_df = pd.DataFrame()
    found_files: list[str] = []

    for folder in source_folders:
        for month in months:
            filepath = folder / f"consumption_counts_{month}.txt"
            if filepath.exists():
                found_files.append(str(filepath))
                df_month = pd.read_csv(filepath, sep="\t", index_col=0)
                df_month.index = df_month.index.str.lower().str.strip().map(std_mapping)
                df_month.columns = df_month.columns.str.lower().str.strip().map(std_mapping)
                total_df = total_df.add(df_month, fill_value=0)

    if not found_files:
        print(
            "\n[warning]  consumption_counts_*.txt  0 \n"
            "   Step 01 generate  CSV   \n"
            "   row: python 02_build_media_consumption_counts.py\n"
            "     02 /01 media  user_bias_scores_*.csv \n"
            f"   directory:\n"
            f"     {rp.MEDIA_EXTERNAL_INFORMATION_CONSUME}\n"
        )
    else:
        print(f"read {len(found_files)} monthlyfile ")

    if total_df.empty:
        final_matrix = pd.DataFrame(0.0, index=ordered_categories, columns=ordered_categories)
    else:
        final_matrix = total_df.groupby(total_df.index).sum().T.groupby(total_df.columns).sum().T
    final_matrix = final_matrix.reindex(index=ordered_categories, columns=ordered_categories).fillna(0)

    print("[done] datamergedone  7x7  ")
    print(final_matrix)

    rp.ensure_dir(rp.INFORMATION_CONSUME_MEDIA_ROOT)
    output_csv = rp.MERGED_CONSUMPTION_MATRIX_CSV
    try:
        final_matrix.to_csv(output_csv)
        print(f"[done] save: {output_csv}")
    except Exception as e:
        print(f"note fileprocessingpatherror save ({e})")

    plt.figure(figsize=(10, 8))
    plot_data = final_matrix.replace(0, 1)

    sns.heatmap(
        plot_data,
        cmap="YlGnBu",
        norm=LogNorm(vmin=plot_data.values.min(), vmax=plot_data.values.max()),
        annot=final_matrix,
        fmt=".0f",
        cbar_kws={"label": "Consumption Count (Log Scale)"},
        linewidths=0.5,
        annot_kws={"size": 10},
    )

    plt.xlabel("Media Political Leaning", fontsize=12, fontweight="bold", labelpad=10)
    plt.ylabel("User Political Leaning", fontsize=12, fontweight="bold", labelpad=10)
    plt.title(
        "Heatmap of Information Consumption by Ideological Alignment",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )
    plt.xticks(rotation=30, ha="right", fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    plt.tight_layout()

    output_img = rp.FIGURE_4A_HEATMAP_PNG
    try:
        plt.savefig(output_img, dpi=300, bbox_inches="tight")
        print(f"[done] save: {output_img}")
    except Exception as e:
        print(f"save: {e}")

    plt.show()


if __name__ == "__main__":
    merge_monthly_consumption_matrices_from_three_sources()
