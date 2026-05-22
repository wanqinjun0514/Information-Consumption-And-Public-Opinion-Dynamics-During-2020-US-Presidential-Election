"""Project workflow helper."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from sankey_paths import (
    MEDIA_DATA_PARTS,
    media_monthly_sankey_dir,
    media_rating_dir,
    month_pairs,
    read_media_monthly_user_bias,
    rp,
)

MEDIA_LABELS_7 = [
    "Extreme bias Left", "Left", "Left leaning", "Center",
    "Right leaning", "Right", "Extreme bias right",
]

NODE_COLOR_MAP_7 = {
    "Extreme bias Left": "rgb(0, 51, 102)",
    "Left": "rgb(51, 102, 153)",
    "Left leaning": "rgb(181, 216, 243)",
    "Center": "rgb(240, 230, 140)",
    "Right leaning": "rgb(255, 153, 153)",
    "Right": "rgb(204, 102, 102)",
    "Extreme bias right": "rgb(139, 26, 26)",
    "DEFAULT": "rgb(128, 128, 128)",
}

LINK_COLOR_MAP_7 = {
    k: f"rgba{v[4:-1]},0.5)" if k != "Center" else "rgba(240, 230, 140, 0.7)"
    for k, v in NODE_COLOR_MAP_7.items()
}


def media_categorize_bias_7(score: float) -> str:
    if -3 <= score < -2.5:
        return "Extreme bias Left"
    if -2.5 <= score < -1.5:
        return "Left"
    if -1.5 <= score < -0.5:
        return "Left leaning"
    if -0.5 <= score < 0.5:
        return "Center"
    if 0.5 <= score < 1.5:
        return "Right leaning"
    if 1.5 <= score < 2.5:
        return "Right"
    if 2.5 <= score <= 3:
        return "Extreme bias right"
    return "Unknown"


def _color_suffix_7(node_name: str) -> str:
    for key in (
        "Extreme bias Left", "Left leaning", "Left", "Center",
        "Right leaning", "Right", "Extreme bias right",
    ):
        if key in node_name:
            return key
    return "DEFAULT"


def find_common_user_between_two_months_by_media(data_part_names=MEDIA_DATA_PARTS):
    for part in data_part_names:
        base = media_rating_dir(part)
        out_dir = rp.ensure_dir(media_monthly_sankey_dir(part, "common_user_bias"))
        for date1, date2 in month_pairs():
            path1 = base / f"user_bias_scores_{date1}.csv"
            path2 = base / f"user_bias_scores_{date2}.csv"
            if not path1.is_file() or not path2.is_file():
                print(f"[skip] {part} missing {date1}  {date2} monthlyfile")
                continue
            df1 = read_media_monthly_user_bias(path1)
            df2 = read_media_monthly_user_bias(path2)
            merged = pd.merge(df1, df2, on="user_id", how="inner")
            merged = merged.rename(columns={
                "average_bias_points_x": "date1_average",
                "average_bias_points_y": "date2_average",
            })
            out = out_dir / f"common_user_bias_{date1}_to_{date2}.csv"
            merged[["user_id", "date1_average", "date2_average"]].to_csv(out, index=False)
            print(f"[{part}] {len(merged)} user -> {out}")


def construct_monthly_cross_table_by_media(data_part_names=MEDIA_DATA_PARTS):
    for part in data_part_names:
        cross_dir = rp.ensure_dir(media_monthly_sankey_dir(part, "cross_table"))
        for date1, date2 in month_pairs():
            inp = media_monthly_sankey_dir(part, "common_user_bias", f"common_user_bias_{date1}_to_{date2}.csv")
            if not inp.is_file():
                print(f"[skip] userfile: {inp}")
                continue
            df = pd.read_csv(inp)
            df["cat1"] = df["date1_average"].apply(media_categorize_bias_7)
            df["cat2"] = df["date2_average"].apply(media_categorize_bias_7)
            transitions = {f"{a} to {b}": 0 for a in MEDIA_LABELS_7 for b in MEDIA_LABELS_7}
            for _, row in df.iterrows():
                key = f'{row["cat1"]} to {row["cat2"]}'
                if key in transitions:
                    transitions[key] += 1
            rows = []
            for k, v in transitions.items():
                s, t = k.split(" to ")
                rows.append({"source": f"{date1}_{s}", "target": f"{date2}_{t}", "value": v})
            out = cross_dir / f"transitions_sankey_{date1}_to_{date2}.csv"
            pd.DataFrame(rows).to_csv(out, index=False)
            print(f"[{part}] crosstab -> {out}")


def validate_transition_value_totals(data_part_names=MEDIA_DATA_PARTS):
    for part in data_part_names:
        folder = media_monthly_sankey_dir(part, "cross_table")
        if not folder.is_dir():
            print(f"[skip] {folder}")
            continue
        print(f"\n=== {part} ===")
        for f in sorted(folder.glob("transitions_sankey_*.csv")):
            df = pd.read_csv(f)
            if "value" in df.columns:
                print(f"{f.name}\tvalue={df['value'].sum()}")


def plot_monthly_sankey_by_media(data_part_names=MEDIA_DATA_PARTS):
    """Project workflow helper."""
    for part in data_part_names:
        for date1, date2 in month_pairs():
            csv_file = media_monthly_sankey_dir(part, "cross_table", f"transitions_sankey_{date1}_to_{date2}.csv")
            if not csv_file.is_file():
                continue
            df = pd.read_csv(csv_file)
            df.columns = ["source", "target", "value"]
            nodes = [
                f"{date1}_{l}" for l in MEDIA_LABELS_7
            ] + [f"{date2}_{l}" for l in MEDIA_LABELS_7]
            node_dict = {n: i for i, n in enumerate(nodes)}
            link_colors = [LINK_COLOR_MAP_7[_color_suffix_7(s)] for s in df["source"]]
            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15, thickness=20, line=dict(color="black", width=0.5),
                    label=nodes, color=[NODE_COLOR_MAP_7[_color_suffix_7(n)] for n in nodes],
                ),
                link=dict(
                    source=df["source"].map(node_dict).astype(int),
                    target=df["target"].map(node_dict).astype(int),
                    value=df["value"], color=link_colors,
                ),
            )])
            fig.update_layout(title_text=f"Media {part}: {date1} -> {date2}", font_size=10)
            fig.show()


def plot_multi_columns_sankey_by_media_monthly(
    data_part_name: str = "without_url",
    data_part_names=None,
):
    """Project workflow helper."""
    parts = (data_part_name,) if data_part_names is None else data_part_names
    for part in parts:
        long_df = pd.DataFrame()
        for date1, date2 in month_pairs():
            csv_file = media_monthly_sankey_dir(part, "cross_table", f"transitions_sankey_{date1}_to_{date2}.csv")
            if not csv_file.is_file():
                print(f"[skip] {csv_file}")
                continue
            temp = pd.read_csv(csv_file)
            temp.columns = ["source", "target", "value"]
            long_df = pd.concat([long_df, temp], ignore_index=True)
        if long_df.empty:
            print(f"[{part}] crosstab skip")
            continue
        nodes = sorted(set(long_df["source"]).union(set(long_df["target"])))
        node_dict = {n: i for i, n in enumerate(nodes)}
        link_colors = [LINK_COLOR_MAP_7[_color_suffix_7(s)] for s in long_df["source"]]
        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15, thickness=20, line=dict(color="black", width=0.5),
                label=[], color=[NODE_COLOR_MAP_7[_color_suffix_7(n)] for n in nodes],
            ),
            link=dict(
                source=long_df["source"].map(node_dict).astype(int),
                target=long_df["target"].map(node_dict).astype(int),
                value=long_df["value"], color=link_colors,
            ),
        )])
        fig.update_layout(
            title_text=f"Media {part}   15-month multi-column Sankey",
            font_size=10, height=800, width=2000,
        )
        fig.show(config={"toImageButtonOptions": {"format": "svg", "filename": f"media_{part}_15m"}})


def change_name_media_monthly(data_part_name: str = "without_url"):
    folder = Path(media_monthly_sankey_dir(data_part_name, "Sankey_plot", "month"))
    if not folder.is_dir():
        print(f"[skip] directory: {folder}")
        return
    new_filenames = [f"common_user_bias_{a}_to_{b}.png" for a, b in month_pairs()]

    def extract_file_number(filename):
        m = re.search(r"newplot(?: \((\d+)\))?.png", filename)
        return int(m.group(1)) if m and m.group(1) else (0 if m else -1)

    images = sorted(
        [f for f in os.listdir(folder) if f.startswith("newplot") and f.endswith(".png")],
        key=extract_file_number,
    )
    if len(images) != len(new_filenames):
        print(f"file: {len(images)} vs {len(new_filenames)}")
        return
    for old, new in zip(images, new_filenames):
        os.rename(folder / old, folder / new)
        print(f"{old} -> {new}")


if __name__ == "__main__":
    find_common_user_between_two_months_by_media()
    construct_monthly_cross_table_by_media()
    # validate_transition_value_totals()
    # change_name_media_monthly()
