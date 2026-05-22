"""Project workflow helper."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from sankey_paths import (
    POLITICIAN_DATA_PARTS,
    month_pairs,
    politician_monthly_dir,
    politician_monthly_sankey_dir,
    politician_rating_dir,
    rp,
)

POLITICIAN_LABELS = ["Left", "Center", "Right"]

NODE_COLOR_MAP_3 = {
    "Left": "rgb(51, 102, 153)",
    "Center": "rgb(240, 230, 140)",
    "Right": "rgb(204, 102, 102)",
    "DEFAULT": "rgb(128, 128, 128)",
}

LINK_COLOR_MAP_3 = {
    "Left": "rgba(51, 102, 153, 0.5)",
    "Center": "rgba(240, 230, 140, 0.7)",
    "Right": "rgba(204, 102, 102, 0.5)",
    "DEFAULT": "rgba(128, 128, 128, 0.5)",
}


def politician_categorize_bias(score: float) -> str:
    if score <= -1 / 3:
        return "Left"
    if score < 1 / 3:
        return "Center"
    return "Right"


def _color_suffix_3(node_name: str) -> str:
    for key in ("Left", "Center", "Right"):
        if key in node_name:
            return key
    return "DEFAULT"


def find_common_user_between_two_months_by_politician(data_part_names=POLITICIAN_DATA_PARTS):
    for part in data_part_names:
        out_dir = rp.ensure_dir(politician_monthly_sankey_dir(part, "common_user_bias"))
        for date1, date2 in month_pairs():
            path1 = politician_monthly_dir(part) / f"{date1}_output.csv"
            path2 = politician_monthly_dir(part) / f"{date2}_output.csv"
            if not path1.is_file() or not path2.is_file():
                print(f"[skip] {part} missingmonthlyfile {date1}  {date2}")
                continue
            df1 = pd.read_csv(
                path1, usecols=["retweeted_user_id", "average_bias_points"],
                dtype={"retweeted_user_id": "str", "average_bias_points": "float64"},
            )
            df2 = pd.read_csv(
                path2, usecols=["retweeted_user_id", "average_bias_points"],
                dtype={"retweeted_user_id": "str", "average_bias_points": "float64"},
            )
            common = set(df1["retweeted_user_id"]) & set(df2["retweeted_user_id"])
            d1 = df1.set_index("retweeted_user_id")["average_bias_points"]
            d2 = df2.set_index("retweeted_user_id")["average_bias_points"]
            rows = {
                "retweeted_user_id": list(common),
                "date1_average": [d1[u] for u in common],
                "date2_average": [d2[u] for u in common],
            }
            out = out_dir / f"common_user_bias_{date1}_to_{date2}.csv"
            pd.DataFrame(rows).to_csv(out, index=False)
            print(f"[{part}] {len(common)} user -> {out}")


def construct_monthly_cross_table_by_politician(data_part_names=POLITICIAN_DATA_PARTS):
    for part in data_part_names:
        cross_dir = rp.ensure_dir(politician_monthly_sankey_dir(part, "cross_table"))
        for date1, date2 in month_pairs():
            inp = politician_monthly_sankey_dir(part, "common_user_bias", f"common_user_bias_{date1}_to_{date2}.csv")
            if not inp.is_file():
                print(f"[skip] {inp}")
                continue
            df = pd.read_csv(inp)
            df["cat1"] = df["date1_average"].apply(politician_categorize_bias)
            df["cat2"] = df["date2_average"].apply(politician_categorize_bias)
            transitions = {f"{a} to {b}": 0 for a in POLITICIAN_LABELS for b in POLITICIAN_LABELS}
            for _, row in df.iterrows():
                transitions[f'{row["cat1"]} to {row["cat2"]}'] += 1
            rows = []
            for k, v in transitions.items():
                s, t = k.split(" to ")
                rows.append({"source": f"{date1}_{s}", "target": f"{date2}_{t}", "value": v})
            out = cross_dir / f"transitions_sankey_{date1}_to_{date2}.csv"
            pd.DataFrame(rows).to_csv(out, index=False)
            print(f"[{part}] crosstab -> {out}")


def plot_monthly_sankey_by_politician(data_part_names=POLITICIAN_DATA_PARTS):
    for part in data_part_names:
        for date1, date2 in month_pairs():
            csv_file = politician_monthly_sankey_dir(part, "cross_table", f"transitions_sankey_{date1}_to_{date2}.csv")
            if not csv_file.is_file():
                continue
            df = pd.read_csv(csv_file)
            nodes = list(set(df["source"]).union(set(df["target"])))
            node_dict = {n: i for i, n in enumerate(nodes)}
            link_colors = [LINK_COLOR_MAP_3[_color_suffix_3(s)] for s in df["source"]]
            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15, thickness=20, line=dict(color="black", width=0.5),
                    label=list(nodes),
                    color=[NODE_COLOR_MAP_3[_color_suffix_3(n)] for n in nodes],
                ),
                link=dict(
                    source=df["source"].map(node_dict).astype(int),
                    target=df["target"].map(node_dict).astype(int),
                    value=df["value"], color=link_colors,
                ),
            )])
            fig.update_layout(title_text=f"Politician {part}: {date1} -> {date2}", font_size=10)
            fig.show()


def plot_multi_columns_sankey_by_politician(data_part_name: str = "without_url"):
    """Project workflow helper."""
    long_df = pd.DataFrame()
    for date1, date2 in month_pairs():
        csv_file = politician_monthly_sankey_dir(
            data_part_name, "cross_table", f"transitions_sankey_{date1}_to_{date2}.csv"
        )
        if not csv_file.is_file():
            print(f"[skip] {csv_file}")
            continue
        temp = pd.read_csv(csv_file)
        temp.columns = ["source", "target", "value"]
        long_df = pd.concat([long_df, temp], ignore_index=True)
    if long_df.empty:
        print("data row ")
        return

    nodes = sorted(set(long_df["source"]).union(set(long_df["target"])))
    node_dict = {n: i for i, n in enumerate(nodes)}
    link_colors = [LINK_COLOR_MAP_3[_color_suffix_3(s)] for s in long_df["source"]]
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15, thickness=20, line=dict(color="black", width=0.5),
            label=[], color=[NODE_COLOR_MAP_3[_color_suffix_3(n)] for n in nodes],
        ),
        link=dict(
            source=long_df["source"].map(node_dict).astype(int),
            target=long_df["target"].map(node_dict).astype(int),
            value=long_df["value"], color=link_colors,
        ),
    )])
    fig.update_layout(
        title_text=f"Politician {data_part_name}   15-month multi-column Sankey",
        font_size=10, height=800, width=2000,
    )
    fig.show(config={"toImageButtonOptions": {"format": "svg", "filename": f"politician_{data_part_name}_15m"}})


def change_name_politician_monthly(data_part_name: str = "without_url"):
    folder = Path(politician_rating_dir(data_part_name) / "sankey_plot" / "Sankey_plot" / "month")
    if not folder.is_dir():
        print(f"[skip] {folder}")
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
    find_common_user_between_two_months_by_politician()
    construct_monthly_cross_table_by_politician()
