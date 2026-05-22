"""Project workflow helper."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from sankey_paths import (
    MEDIA_DATA_PARTS,
    POLITICIAN_DATA_PARTS,
    adjacent_quarter_pairs,
    media_new_user_sankey_dir,
    media_quarterly_file,
    politician_new_user_sankey_dir,
    politician_total_quarterly_file,
    politician_quarterly_file,
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


def media_categorize_bias(score: float) -> str:
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


def politician_categorize_bias(score: float) -> str:
    if score <= -1 / 3:
        return "Left"
    if score < 1 / 3:
        return "Center"
    return "Right"


def _media_color(node_name: str) -> str:
    for key in NODE_COLOR_MAP_7:
        if key in node_name:
            return key
    return "DEFAULT"


def _pol_color(node_name: str) -> str:
    for key in ("Left", "Center", "Right"):
        if key in node_name:
            return key
    return "DEFAULT"


def _quarterly_user_frame(path: Path, id_col: str) -> pd.DataFrame:
    return pd.read_csv(
        path,
        usecols=[id_col, "average_bias_points"],
        dtype={id_col: "str", "average_bias_points": "float64"},
    )


def _build_new_user_transitions(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    id_col: str,
    labels: list[str],
    categorize,
    date1: str,
    date2: str,
) -> pd.DataFrame:
    prev_users = set(df1[id_col])
    curr_users = set(df2[id_col])
    new_users = curr_users - prev_users
    new_df = df2[df2[id_col].isin(new_users)].copy()

    df1 = df1.copy()
    df2 = df2.copy()
    df1["c1"] = df1["average_bias_points"].apply(categorize)
    df2["c2"] = df2["average_bias_points"].apply(categorize)
    new_df["c2"] = new_df["average_bias_points"].apply(categorize)

    transitions = {f"{a} to {b}": 0 for a in labels for b in labels}
    for b in labels:
        transitions[f"New users to {b}"] = 0

    merged = df1.merge(df2, on=id_col, how="inner")
    for _, row in merged.iterrows():
        transitions[f'{row["c1"]} to {row["c2"]}'] += 1
    for _, row in new_df.iterrows():
        transitions[f'New users to {row["c2"]}'] += 1

    rows = []
    for k, v in transitions.items():
        s, t = k.split(" to ")
        rows.append({"source": f"{date1}_{s}", "target": f"{date2}_{t}", "value": v})
    return pd.DataFrame(rows)


def build_media_sankey_crosstabs_with_new_users(
    data_part_names=MEDIA_DATA_PARTS,
):
    for part in data_part_names:
        cross_dir = rp.ensure_dir(media_new_user_sankey_dir(part, "cross_table"))
        for date1, date2 in adjacent_quarter_pairs():
            f1 = media_quarterly_file(part, date1)
            f2 = media_quarterly_file(part, date2)
            if not f1.is_file() or not f2.is_file():
                print(f"[skip] {part} quarterfile: {date1}  {date2}")
                continue
            df1 = _quarterly_user_frame(f1, "user_id")
            df2 = _quarterly_user_frame(f2, "user_id")
            out_df = _build_new_user_transitions(
                df1, df2, "user_id", MEDIA_LABELS_7, media_categorize_bias, date1, date2
            )
            out = cross_dir / f"modified_transitions_sankey_{date1}_to_{date2}.csv"
            out_df.to_csv(out, index=False)
            print(f"[media {part}] -> {out}")


def merge_adjacent_quarter_crosstabs_media(data_part_name: str = "without_url"):
    folder = media_new_user_sankey_dir(data_part_name, "cross_table")
    out = folder / "merged_transitions_sankey.csv"
    parts = sorted(folder.glob("modified_transitions_sankey_*.csv"))
    if not parts:
        print(f"[skip] crosstab: {folder}")
        return
    pd.concat([pd.read_csv(p) for p in parts], ignore_index=True).to_csv(out, index=False)
    print(f"merge -> {out}")


def plot_media_multicolumn_sankey_with_new_users(data_part_name: str = "without_url"):
    csv_file = media_new_user_sankey_dir(data_part_name, "cross_table", "merged_transitions_sankey.csv")
    _plot_multi_column_sankey(csv_file, NODE_COLOR_MAP_7, LINK_COLOR_MAP_7, _media_color,
                              f"Media {data_part_name}   new users multi-column")


def build_politician_sankey_crosstabs_with_new_users(
    use_total_url: bool = True,
    data_part_name: str = "without_url",
):
    """Project workflow helper."""
    labels = ["Left", "Center", "Right"]
    id_col = "retweeted_user_id"
    cross_dir = rp.ensure_dir(
        politician_new_user_sankey_dir(data_part_name, "cross_table")
        if not use_total_url
        else politician_new_user_sankey_dir("total_url", "cross_table")
    )
    for date1, date2 in adjacent_quarter_pairs():
        if use_total_url:
            f1, f2 = politician_total_quarterly_file(date1), politician_total_quarterly_file(date2)
        else:
            f1 = politician_quarterly_file(data_part_name, date1)
            f2 = politician_quarterly_file(data_part_name, date2)
        if not f1.is_file() or not f2.is_file():
            print(f"[skip] quarterfile: {date1}  {date2}")
            continue
        df1 = _quarterly_user_frame(f1, id_col)
        df2 = _quarterly_user_frame(f2, id_col)
        out_df = _build_new_user_transitions(
            df1, df2, id_col, labels, politician_categorize_bias, date1, date2
        )
        out = cross_dir / f"modified_transitions_sankey_{date1}_to_{date2}.csv"
        out_df.to_csv(out, index=False)
        print(f"[politician] -> {out}")


def merge_adjacent_quarter_crosstabs_politician(use_total_url: bool = True, data_part_name: str = "without_url"):
    folder = (
        politician_new_user_sankey_dir("total_url", "cross_table")
        if use_total_url
        else politician_new_user_sankey_dir(data_part_name, "cross_table")
    )
    out = folder / "merged_transitions_sankey.csv"
    parts = sorted(folder.glob("modified_transitions_sankey_*.csv"))
    if not parts:
        print(f"[skip] {folder}")
        return
    pd.concat([pd.read_csv(p) for p in parts], ignore_index=True).to_csv(out, index=False)
    print(f"merge -> {out}")


POL_NODE = {
    "Left": "rgb(51, 102, 153)",
    "Center": "rgb(240, 230, 140)",
    "Right": "rgb(204, 102, 102)",
    "DEFAULT": "rgb(128, 128, 128)",
}
POL_LINK = {
    "Left": "rgba(51, 102, 153, 0.5)",
    "Center": "rgba(240, 230, 140, 0.7)",
    "Right": "rgba(204, 102, 102, 0.5)",
    "DEFAULT": "rgba(128, 128, 128, 0.5)",
}


def plot_politician_multicolumn_sankey_with_new_users(use_total_url: bool = True, data_part_name: str = "without_url"):
    folder = (
        politician_new_user_sankey_dir("total_url", "cross_table")
        if use_total_url
        else politician_new_user_sankey_dir(data_part_name, "cross_table")
    )
    csv_file = folder / "merged_transitions_sankey.csv"
    title = "Politician total_url   new users multi-column" if use_total_url else f"Politician {data_part_name}"
    _plot_multi_column_sankey(csv_file, POL_NODE, POL_LINK, _pol_color, title)


def _plot_multi_column_sankey(csv_file, node_map, link_map, suffix_fn, title: str):
    if not Path(csv_file).is_file():
        print(f"[skip] missing: {csv_file}")
        return
    long_df = pd.read_csv(csv_file)
    long_df.columns = ["source", "target", "value"]
    nodes = sorted(set(long_df["source"]).union(set(long_df["target"])))
    node_dict = {n: i for i, n in enumerate(nodes)}
    link_colors = [link_map[suffix_fn(s)] for s in long_df["source"]]
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15, thickness=20, line=dict(color="black", width=0.5),
            label=nodes, color=[node_map[suffix_fn(n)] for n in nodes],
        ),
        link=dict(
            source=long_df["source"].map(node_dict).astype(int),
            target=long_df["target"].map(node_dict).astype(int),
            value=long_df["value"], color=link_colors,
        ),
    )])
    fig.update_layout(title_text=title, font_size=10, height=800, width=2200)
    fig.show()


if __name__ == "__main__":
    build_media_sankey_crosstabs_with_new_users()
    merge_adjacent_quarter_crosstabs_media(data_part_name="without_url")
    # plot_media_multicolumn_sankey_with_new_users(data_part_name="without_url")

    build_politician_sankey_crosstabs_with_new_users(use_total_url=True)
    merge_adjacent_quarter_crosstabs_politician(use_total_url=True)
    # plot_politician_multicolumn_sankey_with_new_users(use_total_url=True)
