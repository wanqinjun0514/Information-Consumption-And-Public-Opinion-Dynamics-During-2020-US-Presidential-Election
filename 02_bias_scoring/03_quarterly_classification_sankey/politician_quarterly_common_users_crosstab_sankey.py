import glob
import os
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

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

POLITICIAN_DATA_PARTS = ("external_url", "twitter_url", "without_url")

QUARTER_MONTHS = [
    ["2019_12", "2020_01", "2020_02"],
    ["2020_03", "2020_04", "2020_05"],
    ["2020_06", "2020_07", "2020_08"],
    ["2020_09", "2020_10"],
    ["2020_11", "2020_12"],
    ["2021_01", "2021_02"],
]

QUARTER_LABELS = ["_".join(m) for m in QUARTER_MONTHS]

QUARTER_AVG_COLUMNS = [f"{q}_average_bias_points" for q in QUARTER_LABELS]

POLITICIAN_LCR_GROUPS = ("center_user", "left_user", "right_user")


def politician_part_quarterly_dir(data_part_name: str) -> Path:
    return rp.DIR_02_POLITICIAN_RATING_ROOT / f"{data_part_name}-rating" / "quaterly_users_bias"


def politician_total_quarter_dir() -> Path:
    return rp.DIR_02_POLITICIAN_RATING_ROOT / "total_url-rating" / "user_bias_scores_by_quarter"


def _read_politician_monthly(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        dtype={
            "retweeted_user_id": "str",
            "total_bias_points": "float64",
            "retweet_times": "int64",
        },
    )
    needed = {"retweeted_user_id", "total_bias_points", "retweet_times"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"{path} missingcolumn: {missing}")
    return df[list(needed)]


def process_quarterly_politician_user_bias_scores(data_part_names=POLITICIAN_DATA_PARTS):
    """Project workflow helper."""
    for data_part_name in data_part_names:
        monthly_dir = rp.DIR_02_POLITICIAN_RATING_ROOT / f"{data_part_name}-rating" / "monthly_users_bias"
        out_dir = rp.ensure_dir(politician_part_quarterly_dir(data_part_name))
        print(f"[politicianquartermerge] part={data_part_name}  monthly={monthly_dir}")

        for months in QUARTER_MONTHS:
            quarterly_data = pd.DataFrame()
            for month in months:
                file_path = monthly_dir / f"{month}_output.csv"
                if not file_path.is_file():
                    print(f"  [skip] monthlyfile: {file_path.name}")
                    continue
                temp_df = _read_politician_monthly(file_path)
                if quarterly_data.empty:
                    quarterly_data = temp_df
                else:
                    quarterly_data = pd.concat([quarterly_data, temp_df], ignore_index=True)
                    quarterly_data = quarterly_data.groupby("retweeted_user_id", as_index=False).agg(
                        {"total_bias_points": "sum", "retweet_times": "sum"}
                    )

            if quarterly_data.empty:
                print(f"  [skip] quarter {'_'.join(months)} monthlydata")
                continue

            quarterly_data["average_bias_points"] = (
                quarterly_data["total_bias_points"] / quarterly_data["retweet_times"]
            )
            quarter_str = "_".join(months)
            output_file = out_dir / f"quarterly_user_bias_scores_{quarter_str}.csv"
            quarterly_data.to_csv(output_file, index=False)
            print(f"  save: {output_file}")


def merge_politician_lcr_quarterly_bias_data(data_part_names=POLITICIAN_DATA_PARTS):
    """Project workflow helper."""
    columns = ["retweeted_user_id", "total_bias_points", "retweet_times", "average_bias_points"]

    for data_part_name in data_part_names:
        base_folder = politician_part_quarterly_dir(data_part_name)
        if not base_folder.is_dir():
            print(f"[skip LCR] directory: {base_folder}")
            continue

        has_any_lcr = any((base_folder / g).is_dir() for g in POLITICIAN_LCR_GROUPS)
        if not has_any_lcr:
            print(
                f"[skip LCR] {data_part_name}  center/left/right directory "
                " monthly quarterly  "
            )
            continue

        for quarter in QUARTER_LABELS:
            all_data = pd.DataFrame(columns=columns)
            found = 0
            for user_group in POLITICIAN_LCR_GROUPS:
                file_path = base_folder / user_group / f"{quarter}_{user_group}.csv"
                if file_path.is_file():
                    all_data = pd.concat([all_data, pd.read_csv(file_path)], ignore_index=True)
                    found += 1
                else:
                    print(f"  [] {file_path}")

            output_file = base_folder / f"quarterly_user_bias_scores_{quarter}.csv"
            if found == 0:
                print(f"  [skip] {quarter}  LCR file  {output_file.name}")
                continue
            rp.ensure_dir(output_file.parent)
            all_data.to_csv(output_file, index=False)
            print(f"  [LCR merge] save: {output_file}")


def merge_politician_parts_quarterly_bias_to_total():
    save_path = rp.ensure_dir(politician_total_quarter_dir())
    part_dirs = [politician_part_quarterly_dir(p) for p in POLITICIAN_DATA_PARTS]

    for quarter in QUARTER_LABELS:
        data_frames = []
        for path in part_dirs:
            file_path = path / f"quarterly_user_bias_scores_{quarter}.csv"
            if not file_path.is_file():
                print(f"[warning] : {file_path}")
                continue
            df = pd.read_csv(file_path, encoding="utf-8")
            if {"retweeted_user_id", "total_bias_points", "retweet_times"} <= set(df.columns):
                data_frames.append(df[["retweeted_user_id", "total_bias_points", "retweet_times"]])
            else:
                print(f"[warning] column: {file_path}")

        if not data_frames:
            print(f"[skip] quarter {quarter} data")
            continue

        combined = pd.concat(data_frames, ignore_index=True)
        merged_df = combined.groupby("retweeted_user_id", as_index=False).agg(
            {"total_bias_points": "sum", "retweet_times": "sum"}
        )
        output_file = save_path / f"quarterly_user_bias_scores_{quarter}.csv"
        merged_df.to_csv(output_file, index=False, encoding="utf-8")
        print(f"quarter {quarter} save: {output_file}")

    print("quartermergedone ")


def add_average_bias_to_merged_total():
    dir_path = politician_total_quarter_dir()
    if not dir_path.is_dir():
        print(f"[skip] directory: {dir_path}")
        return

    file_list = sorted(dir_path.glob("quarterly_user_bias_scores_*.csv"))
    if not file_list:
        print(f"quarter CSV: {dir_path}")
        return

    for file_path in file_list:
        df = pd.read_csv(file_path, encoding="utf-8")
        if {"total_bias_points", "retweet_times"} <= set(df.columns):
            df["average_bias_points"] = df["total_bias_points"] / df["retweet_times"]
            df.to_csv(file_path, index=False, encoding="utf-8")
            print(f": {file_path.name}")
        else:
            print(f"skip column : {file_path.name}")


def find_politician_users_present_in_all_quarters():
    dir_path = politician_total_quarter_dir()
    file_list = sorted(glob.glob(str(dir_path / "quarterly_user_bias_scores_*.csv")))
    if not file_list:
        print(f"quarterfile: {dir_path}")
        return

    quarter_data = []
    for file_path in file_list:
        filename = os.path.basename(file_path)
        quarter_name = filename[len("quarterly_user_bias_scores_") : -len(".csv")]
        column_name = quarter_name + "_average_bias_points"
        quarter_data.append((quarter_name, column_name, file_path))
    quarter_data.sort()

    data_frames = []
    quarter_column_names = []
    for _qn, column_name, file_path in quarter_data:
        df = pd.read_csv(file_path, encoding="utf-8")
        df = df[["retweeted_user_id", "average_bias_points"]]
        df.rename(columns={"average_bias_points": column_name}, inplace=True)
        data_frames.append(df)
        quarter_column_names.append(column_name)

    merged_df = data_frames[0]
    for df in data_frames[1:]:
        merged_df = pd.merge(merged_df, df, on="retweeted_user_id", how="inner")

    output_columns = ["retweeted_user_id"] + quarter_column_names
    merged_df = merged_df[output_columns]
    output_file = dir_path / "all_quaters_common_users_merged_user_average_bias_points.csv"
    merged_df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"quarteruser {len(merged_df)}  -> {output_file}")


def _politician_categorize_bias(score):
    if score <= -1 / 3:
        return "Left"
    if score < 1 / 3:
        return "Center"
    return "Right"


def count_politician_bias_categories_by_quarter():
    input_path = politician_total_quarter_dir() / "all_quaters_common_users_merged_user_average_bias_points.csv"
    if not input_path.is_file():
        print(f"[skip] row find_politician_users_present_in_all_quarters : {input_path}")
        return

    df = pd.read_csv(input_path, encoding="utf-8")
    categories = ["Left", "Center", "Right"]
    category_counts_list = []

    for quarter in QUARTER_AVG_COLUMNS:
        if quarter not in df.columns:
            continue
        df[quarter + "_category"] = df[quarter].apply(_politician_categorize_bias)
        counts = df[quarter + "_category"].value_counts().reindex(categories, fill_value=0)
        counts["quarter_total"] = counts.sum()
        counts.name = quarter.replace("_average_bias_points", "")
        category_counts_list.append(counts)

    category_counts_df = pd.DataFrame(category_counts_list)
    category_counts_df.reset_index(inplace=True)
    category_counts_df.rename(columns={"index": "Quarter"}, inplace=True)
    columns_order = ["Quarter"] + categories + ["quarter_total"]
    category_counts_df = category_counts_df[columns_order]

    output_path = politician_total_quarter_dir() / "category_counts.csv"
    category_counts_df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"save: {output_path}")


def build_politician_quarterly_bias_transition_crosstabs():
    file_path = politician_total_quarter_dir() / "all_quaters_common_users_merged_user_average_bias_points.csv"
    if not file_path.is_file():
        print(f"[skip] missinguser: {file_path}")
        return

    df = pd.read_csv(file_path)
    labels = ["Left", "Center", "Right"]
    columns = [c for c in QUARTER_AVG_COLUMNS if c in df.columns]

    for col in columns:
        df[f"category_{col}"] = df[col].apply(_politician_categorize_bias)

    all_transitions_data = []
    for i in range(len(columns) - 1):
        col1 = f"category_{columns[i]}"
        col2 = f"category_{columns[i + 1]}"
        transitions = {f"{l1} to {l2}": 0 for l1 in labels for l2 in labels}
        for _, row in df.iterrows():
            transitions[f"{row[col1]} to {row[col2]}"] += 1
        for k, v in transitions.items():
            source, target = k.split(" to ")
            all_transitions_data.append(
                {
                    "source": f"{columns[i]}_{source}",
                    "target": f"{columns[i + 1]}_{target}",
                    "value": v,
                }
            )

    output_path = politician_total_quarter_dir() / "all_quaters_users_transitions_sankey.csv"
    pd.DataFrame(all_transitions_data).to_csv(output_path, index=False)
    print(f"save: {output_path}")


def plot_politician_multicolumn_sankey():
    csv_file = politician_total_quarter_dir() / "all_quaters_users_transitions_sankey.csv"
    if not csv_file.is_file():
        print(f"[skip] missing: {csv_file}")
        return

    long_df = pd.read_csv(csv_file)
    long_df.columns = ["source", "target", "value"]

    nodes = list(set(long_df["source"]).union(set(long_df["target"])))
    node_dict = {node: i for i, node in enumerate(nodes)}

    def extract_color_suffix(node_name):
        for key in ("Left", "Center", "Right"):
            if key in node_name:
                return key
        return "DEFAULT"

    node_color_map = {
        "Left": "rgb(51, 102, 153)",
        "Center": "rgb(240, 230, 140)",
        "Right": "rgb(204, 102, 102)",
        "DEFAULT": "rgb(128, 128, 128)",
    }
    link_color_map = {
        "Left": "rgba(51, 102, 153, 0.5)",
        "Center": "rgba(240, 230, 140, 0.7)",
        "Right": "rgba(204, 102, 102, 0.5)",
        "DEFAULT": "rgba(128, 128, 128, 0.5)",
    }

    node_colors = [node_color_map[extract_color_suffix(n)] for n in nodes]
    link_colors = [link_color_map[extract_color_suffix(s)] for s in long_df["source"]]

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=nodes,
                    color=node_colors,
                ),
                link=dict(
                    source=long_df["source"].map(node_dict).astype(int),
                    target=long_df["target"].map(node_dict).astype(int),
                    value=long_df["value"],
                    color=link_colors,
                ),
            )
        ]
    )
    fig.update_layout(title_text="Politician multi-quarter Sankey (3-class)", font_size=10)
    fig.show()


if __name__ == "__main__":
    process_quarterly_politician_user_bias_scores()
    merge_politician_lcr_quarterly_bias_data()
    merge_politician_parts_quarterly_bias_to_total()
    add_average_bias_to_merged_total()
    find_politician_users_present_in_all_quarters()
    count_politician_bias_categories_by_quarter()
    build_politician_quarterly_bias_transition_crosstabs()
    plot_politician_multicolumn_sankey()
