import os
import re
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

MEDIA_DATA_PARTS = ("external_url", "twitter_url", "without_url")

QUARTER_MONTHS = [
    ["2019_12", "2020_01", "2020_02"],
    ["2020_03", "2020_04", "2020_05"],
    ["2020_06", "2020_07", "2020_08"],
    ["2020_09", "2020_10"],
    ["2020_11", "2020_12"],
    ["2021_01", "2021_02"],
]

QUARTER_FILE_NAMES = [
    f"quarterly_user_bias_scores_{'_'.join(months)}.csv" for months in QUARTER_MONTHS
]

SANKEY_DATE1S = [f"{'_'.join(q)}" for q in QUARTER_MONTHS[:-1]]
SANKEY_DATE2S = [f"{'_'.join(q)}" for q in QUARTER_MONTHS[1:]]


def media_rating_dir(data_part_name: str) -> Path:
    return rp.DIR_02_MEDIA_RATING_ROOT / f"{data_part_name}-rating"


def media_sankey_dir(data_part_name: str, *parts: str) -> Path:
    return media_rating_dir(data_part_name) / "sankey_plot" / Path(*parts)


def _read_monthly_user_bias(file_path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        file_path,
        dtype={"user_id": "str", "total_score": "float64", "appearance_count": "int64"},
    )
    needed = {"user_id", "total_score", "appearance_count"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"{file_path} missingcolumn: {missing}")
    return df[list(needed)]


def process_quarterly_user_bias_scores(data_part_names=MEDIA_DATA_PARTS):
    """Project workflow helper."""
    for data_part_name in data_part_names:
        base_path = media_rating_dir(data_part_name)
        print(f"[quartermerge] data_part={data_part_name}  base_path={base_path}")

        for months in QUARTER_MONTHS:
            quarterly_data = pd.DataFrame()

            for month in months:
                file_path = base_path / f"user_bias_scores_{month}.csv"
                if not file_path.is_file():
                    print(f"  [skip] monthlyfile: {file_path.name}")
                    continue

                temp_df = _read_monthly_user_bias(file_path)
                if quarterly_data.empty:
                    quarterly_data = temp_df
                else:
                    quarterly_data = pd.concat([quarterly_data, temp_df], ignore_index=True)
                    quarterly_data = quarterly_data.groupby("user_id", as_index=False).agg(
                        {"total_score": "sum", "appearance_count": "sum"}
                    )

            if quarterly_data.empty:
                print(f"  [skip] quarter {'_'.join(months)} monthlydata")
                continue

            quarterly_data["average_bias_points"] = (
                quarterly_data["total_score"] / quarterly_data["appearance_count"]
            )
            quarter_str = "_".join(months)
            output_file = base_path / f"quarterly_user_bias_scores_{quarter_str}.csv"
            quarterly_data.to_csv(output_file, index=False)
            print(f"  save: {output_file}")


def find_common_users_between_quarters(data_part_names=MEDIA_DATA_PARTS):
    """Project workflow helper."""
    for data_part_name in data_part_names:
        base_path = media_rating_dir(data_part_name)
        out_dir = rp.ensure_dir(media_sankey_dir(data_part_name, "every_quarter", "common_user_bias"))

        for i in range(len(QUARTER_FILE_NAMES) - 1):
            path1 = base_path / QUARTER_FILE_NAMES[i]
            path2 = base_path / QUARTER_FILE_NAMES[i + 1]
            if not path1.is_file() or not path2.is_file():
                print(f"[skip] {data_part_name} missingquarterfile: {path1.name}  {path2.name}")
                continue

            q1_str = QUARTER_FILE_NAMES[i].replace("quarterly_user_bias_scores_", "").replace(".csv", "")
            q2_str = QUARTER_FILE_NAMES[i + 1].replace("quarterly_user_bias_scores_", "").replace(".csv", "")
            output_path = out_dir / f"common_users_{q1_str}_to_{q2_str}.csv"

            df1 = pd.read_csv(
                path1,
                usecols=["user_id", "average_bias_points"],
                dtype={"user_id": "str", "average_bias_points": "float64"},
            )
            df2 = pd.read_csv(
                path2,
                usecols=["user_id", "average_bias_points"],
                dtype={"user_id": "str", "average_bias_points": "float64"},
            )
            df1 = df1.rename(columns={"average_bias_points": "date1_average"})
            df2 = df2.rename(columns={"average_bias_points": "date2_average"})
            common_users = pd.merge(df1, df2, on="user_id")
            common_users.to_csv(output_path, index=False)
            print(f"[{data_part_name}] save {len(common_users)} user -> {output_path}")


def Construct_matrix_data_for_drawing_Sankey_diagrams_by_media(data_part_names=MEDIA_DATA_PARTS):
    labels = [
        "Extreme bias Left",
        "Left",
        "Left leaning",
        "Center",
        "Right leaning",
        "Right",
        "Extreme bias right",
    ]

    def categorize_bias(score):
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

    for data_part_name in data_part_names:
        cross_dir = rp.ensure_dir(media_sankey_dir(data_part_name, "every_quarter", "cross_table"))

        for date1, date2 in zip(SANKEY_DATE1S, SANKEY_DATE2S):
            file_path = media_sankey_dir(
                data_part_name, "every_quarter", "common_user_bias", f"common_users_{date1}_to_{date2}.csv"
            )
            if not file_path.is_file():
                print(f"[skip] userfile: {file_path}")
                continue

            output_transition_matrix_path = cross_dir / f"transitions_sankey_{date1}_to_{date2}.csv"
            df = pd.read_csv(file_path)
            df["date1_average"] = df["date1_average"].apply(categorize_bias)
            df["date2_average"] = df["date2_average"].apply(categorize_bias)

            transitions = {f"{l1} to {l2}": 0 for l1 in labels for l2 in labels}
            for _, row in df.iterrows():
                key = f'{row["date1_average"]} to {row["date2_average"]}'
                if key in transitions:
                    transitions[key] += 1

            transitions_data = []
            for k, v in transitions.items():
                source, target = k.split(" to ")
                transitions_data.append(
                    {"source": f"{date1}_{source}", "target": f"{date2}_{target}", "value": v}
                )
            pd.DataFrame(transitions_data).to_csv(output_transition_matrix_path, index=False)
            print(f"[{data_part_name}] crosstab -> {output_transition_matrix_path}")


def validate_transition_value_totals(data_part_names=MEDIA_DATA_PARTS):
    for data_part_name in data_part_names:
        folder_path = media_sankey_dir(data_part_name, "every_quarter", "cross_table")
        if not folder_path.is_dir():
            print(f"[skip] directory: {folder_path}")
            continue
        print(f"\n=== {data_part_name} ===")
        print("file\tvaluecolumn")
        for file in sorted(folder_path.glob("*.csv")):
            df = pd.read_csv(file)
            if "value" in df.columns:
                print(f"{file.name}\t{df['value'].sum()}")


def plot_quaterly_sankey_by_meida(data_part_names=MEDIA_DATA_PARTS):
    for data_part_name in data_part_names:
        for date1, date2 in zip(SANKEY_DATE1S, SANKEY_DATE2S):
            csv_file = media_sankey_dir(
                data_part_name, "every_quarter", "cross_table", f"transitions_sankey_{date1}_to_{date2}.csv"
            )
            if not csv_file.is_file():
                print(f"[skip] crosstab: {csv_file}")
                continue

            df = pd.read_csv(csv_file)
            df.columns = ["source", "target", "value"]
            nodes = [
                f"{date1}_Extreme bias Left",
                f"{date1}_Left",
                f"{date1}_Left leaning",
                f"{date1}_Center",
                f"{date1}_Right leaning",
                f"{date1}_Right",
                f"{date1}_Extreme bias right",
                f"{date2}_Extreme bias Left",
                f"{date2}_Left",
                f"{date2}_Left leaning",
                f"{date2}_Center",
                f"{date2}_Right leaning",
                f"{date2}_Right",
                f"{date2}_Extreme bias right",
            ]
            node_dict = {node: i for i, node in enumerate(nodes)}

            def extract_color_suffix(node_name):
                for key in (
                    "Extreme bias Left",
                    "Left leaning",
                    "Left",
                    "Center",
                    "Right leaning",
                    "Right",
                    "Extreme bias right",
                ):
                    if key in node_name:
                        return key
                return "DEFAULT"

            node_color_map = {
                "Extreme bias Left": "rgb(0, 51, 102)",
                "Left": "rgb(51, 102, 153)",
                "Left leaning": "rgb(181, 216, 243)",
                "Center": "rgb(240, 230, 140)",
                "Right leaning": "rgb(255, 153, 153)",
                "Right": "rgb(204, 102, 102)",
                "Extreme bias right": "rgb(139, 26, 26)",
                "DEFAULT": "rgb(128, 128, 128)",
            }
            link_color_map = {
                "Extreme bias Left": "rgba(0, 51, 102, 0.5)",
                "Left": "rgba(51, 102, 153, 0.5)",
                "Left leaning": "rgba(181, 216, 243, 0.5)",
                "Center": "rgba(240, 230, 140, 0.7)",
                "Right leaning": "rgba(255, 153, 153, 0.5)",
                "Right": "rgba(204, 102, 102, 0.5)",
                "Extreme bias right": "rgba(139, 26, 26, 0.5)",
                "DEFAULT": "rgb(128, 128, 128)",
            }

            node_colors = [node_color_map[extract_color_suffix(node)] for node in nodes]
            link_colors = [link_color_map[extract_color_suffix(link["source"])] for _, link in df.iterrows()]
            link = {
                "source": df["source"].map(node_dict).astype(int),
                "target": df["target"].map(node_dict).astype(int),
                "value": df["value"],
                "color": link_colors,
            }
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
                        link=link,
                    )
                ]
            )
            fig.update_layout(
                title_text=f"Media Sankey ({data_part_name}): {date1} -> {date2}",
                font_size=10,
            )
            fig.show()


def quaterly_change_name(data_part_names=MEDIA_DATA_PARTS):
    new_filenames = [
        "common_user_bias_2019_12_2020_01_2020_02_to_2020_03_2020_04_2020_05.png",
        "common_user_bias_2020_03_2020_04_2020_05_to_2020_06_2020_07_2020_08.png",
        "common_user_bias_2020_06_2020_07_2020_08_to_2020_09_2020_10.png",
        "common_user_bias_2020_09_2020_10_to_2020_11_2020_12.png",
        "common_user_bias_2020_11_2020_12_to_2021_01_2021_02.png",
    ]

    def extract_file_number(filename):
        match = re.search(r"newplot(?: \((\d+)\))?.png", filename)
        if match:
            return int(match.group(1)) if match.group(1) else 0
        return -1

    for data_part_name in data_part_names:
        folder_path = media_sankey_dir(data_part_name, "every_quarter", "Sankey_plot")
        if not folder_path.is_dir():
            print(f"[skip] directory: {folder_path}")
            continue

        image_files = sorted(
            [f for f in os.listdir(folder_path) if f.startswith("newplot") and f.endswith(".png")],
            key=extract_file_number,
        )
        if len(image_files) != len(new_filenames):
            print(f"[{data_part_name}] file: {len(image_files)} vs {len(new_filenames)}")
            continue
        for image_file, new_name in zip(image_files, new_filenames):
            os.rename(folder_path / image_file, folder_path / new_name)
            print(f"[{data_part_name}] {image_file} -> {new_name}")





def find_users_present_in_all_quarters():
    data_part_name = 'twitter_url'
    # data_part_name = 'without_url'
    dir_path = fr'F:\Experimental Results\Average_Bias_Rating\media_average_rating\{data_part_name}-rating'

    file_pattern = os.path.join(dir_path, 'quarterly_user_bias_scores_*.csv')
    file_list = glob.glob(file_pattern)

    quarter_data = []

    for file_path in file_list:
        filename = os.path.basename(file_path)
        quarter_name = filename[len('quarterly_user_bias_scores_'):-len('.csv')]
        column_name = quarter_name + '_average_bias_points'
        quarter_data.append((quarter_name, column_name, file_path))

    quarter_data.sort()

    data_frames = []
    quarter_column_names = []

    for quarter_name, column_name, file_path in quarter_data:
        df = pd.read_csv(file_path, encoding='utf-8')
        df = df[['user_id', 'average_bias_points']]
        df.rename(columns={'average_bias_points': column_name}, inplace=True)
        data_frames.append(df)
        quarter_column_names.append(column_name)

    merged_df = data_frames[0]
    for df in data_frames[1:]:
        merged_df = pd.merge(merged_df, df, on='user_id', how='inner')

    output_columns = ['user_id'] + quarter_column_names
    merged_df = merged_df[output_columns]

    output_file = os.path.join(dir_path, 'all_quaters_common_users_merged_user_average_bias_points.csv')
    merged_df.to_csv(output_file, index=False, encoding='utf-8')

    print("dataprocessdone save ", output_file)


def count_bias_categories_by_quarter():
    df = pd.read_csv(
        r'F:\Experimental Results\Average_Bias_Rating\media_average_rating\external_url-rating\sankey_plot\all_quarters\all_quaters_common_users_merged_user_average_bias_points.csv',
        encoding='utf-8')

    quarters = [
        '2019_12_2020_01_2020_02_average_bias_points',
        '2020_03_2020_04_2020_05_average_bias_points',
        '2020_06_2020_07_2020_08_average_bias_points',
        '2020_09_2020_10_average_bias_points',
        '2020_11_2020_12_average_bias_points',
        '2021_01_2021_02_average_bias_points'
    ]

    def categorize_bias(score):
        if -3 <= score < -2.5:
            return 'Extreme bias Left'
        elif -2.5 <= score < -1.5:
            return 'Left'
        elif -1.5 <= score < -0.5:
            return 'Left leaning'
        elif -0.5 <= score < 0.5:
            return 'Center'
        elif 0.5 <= score < 1.5:
            return 'Right leaning'
        elif 1.5 <= score < 2.5:
            return 'Right'
        elif 2.5 <= score <= 3:
            return 'Extreme bias Right'
        else:
            return 'Unknown'

    categories = [
        'Extreme bias Left',
        'Left',
        'Left leaning',
        'Center',
        'Right leaning',
        'Right',
        'Extreme bias Right',
        'Unknown'
    ]

    for quarter in quarters:
        df[quarter + '_category'] = df[quarter].apply(categorize_bias)

    category_counts_list = []

    for quarter in quarters:
        category_col = quarter + '_category'
        counts = df[category_col].value_counts()
        counts = counts.reindex(categories, fill_value=0)
        total = counts.sum()
        counts['quarter_total'] = total
        quarter_name = quarter.replace('_average_bias_points', '')
        counts.name = quarter_name
        category_counts_list.append(counts)

    category_counts_df = pd.DataFrame(category_counts_list)

    category_counts_df.reset_index(inplace=True)
    category_counts_df.rename(columns={'index': 'Quarter'}, inplace=True)

    columns_order = ['Quarter'] + categories + ['quarter_total']
    category_counts_df = category_counts_df[columns_order]

    output_path = r'F:\Experimental Results\Average_Bias_Rating\media_average_rating\external_url-rating\sankey_plot\all_quarters\category_counts.csv'
    category_counts_df.to_csv(output_path, index=False, encoding='utf-8')

def build_quarterly_bias_transition_crosstabs():
    file_path = r'F:\Experimental Results\Average_Bias_Rating\media_average_rating\external_url-rating\sankey_plot\all_quarters\all_quaters_common_users_merged_user_average_bias_points.csv'
    df = pd.read_csv(file_path)

    bins = [-3, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3]
    labels = ['Extreme bias Left', 'Left', 'Left leaning', 'Center', 'Right leaning', 'Right', 'Extreme bias right']

    def categorize_bias(score):
        if -3 <= score < -2.5:
            return 'Extreme bias Left'
        elif -2.5 <= score < -1.5:
            return 'Left'
        elif -1.5 <= score < -0.5:
            return 'Left leaning'
        elif -0.5 <= score < 0.5:
            return 'Center'
        elif 0.5 <= score < 1.5:
            return 'Right leaning'
        elif 1.5 <= score < 2.5:
            return 'Right'
        elif 2.5 <= score <= 3:
            return 'Extreme bias right'
        else:
            return 'Unknown'

    columns = [
        '2019_12_2020_01_2020_02_average_bias_points',
        '2020_03_2020_04_2020_05_average_bias_points',
        '2020_06_2020_07_2020_08_average_bias_points',
        '2020_09_2020_10_average_bias_points',
        '2020_11_2020_12_average_bias_points',
        '2021_01_2021_02_average_bias_points'
    ]

    for col in columns:
        df[f'category_{col}'] = df[col].apply(categorize_bias)

    all_transitions_data = []

    for i in range(len(columns) - 1):
        col1 = f'category_{columns[i]}'
        col2 = f'category_{columns[i + 1]}'

        transitions = {f'{l1} to {l2}': 0 for l1 in labels for l2 in labels}

        for _, row in df.iterrows():
            transitions[f'{row[col1]} to {row[col2]}'] += 1

        for k, v in transitions.items():
            source, target = k.split(' to ')
            all_transitions_data.append({
                'source': f'{columns[i]}_{source}',
                'target': f'{columns[i + 1]}_{target}',
                'value': v
            })

    all_transitions_df = pd.DataFrame(all_transitions_data)
    output_path = r'F:\Experimental Results\Average_Bias_Rating\media_average_rating\external_url-rating\sankey_plot\all_quarters\all_quaters_users_transitions_sankey.csv'
    all_transitions_df.to_csv(output_path, index=False)


def plot_multicolumn_sankey():
    csv_file = rf'F:\Experimental Results\Average_Bias_Rating\media_average_rating\external_url-rating\sankey_plot\all_quarters\\all_quaters_users_transitions_sankey.csv'
    df = pd.read_csv(csv_file)
    col_names = ['source', 'target', 'value']
    long_df = pd.DataFrame()
    for i in range(0, df.shape[1], 3):
        temp_df = pd.DataFrame(df.iloc[:, i:i + 3].values, columns=col_names)
        long_df = pd.concat([long_df, temp_df])
    long_df.reset_index(drop=True, inplace=True)
    nodes = list(set(long_df['source']).union(set(long_df['target'])))
    print("nodes:",nodes)
    node_dict = {node: i for i, node in enumerate(nodes)}

    def extract_color_suffix(node_name):
        if 'Extreme bias Left' in node_name:
            return 'Extreme bias Left'
        elif 'Left leaning' in node_name:
            return 'Left leaning'
        elif 'Left' in node_name:
            return 'Left'
        elif 'Center' in node_name:
            return 'Center'
        elif 'Right leaning' in node_name:
            return 'Right leaning'
        elif 'Right' in node_name:
            return 'Right'
        elif 'Extreme bias right' in node_name:
            return 'Extreme bias right'
        else:
            return 'DEFAULT'

    node_color_map = {
        'Extreme bias Left': 'rgb(0, 51, 102)',
        'Left': 'rgb(51, 102, 153)',
        'Left leaning': 'rgb(181, 216, 243)',
        'Center': 'rgb(240, 230, 140)',
        'Right leaning': 'rgb(255, 153, 153)',
        'Right': 'rgb(204, 102, 102)',
        'Extreme bias right': 'rgb(139, 26, 26)',
        'DEFAULT': 'rgb(128, 128, 128)'
    }

    link_color_map = {
        'Extreme bias Left': 'rgba(0, 51, 102, 0.5)',
        'Left': 'rgba(51, 102, 153, 0.5)',
        'Left leaning': 'rgba(181, 216, 243, 0.5)',
        'Center': 'rgba(240, 230, 140, 0.7)',
        'Right leaning': 'rgba(255, 153, 153, 0.5)',
        'Right': 'rgba(204, 102, 102, 0.5)',
        'Extreme bias right': 'rgba(139, 26, 26, 0.5)',
        'DEFAULT': 'rgb(128, 128, 128)'
    }

    node_colors = [node_color_map[extract_color_suffix(node)] for node in nodes]
    link_colors = [link_color_map[extract_color_suffix(long_df.iloc[i]['source'])] for i in range(len(long_df))]

    link = {
        'source': long_df['source'].map(node_dict).astype(int),
        'target': long_df['target'].map(node_dict).astype(int),
        'value': long_df['value'],
        'color': link_colors
    }

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=[node for node in node_dict],
            color=node_colors
        ),
        link=link
    )])

    fig.update_layout(title_text="Time Series Sankey Diagram", font_size=10)
    fig.show()



if __name__ == "__main__":
    # process_quarterly_user_bias_scores()
    # find_common_users_between_quarters()
    Construct_matrix_data_for_drawing_Sankey_diagrams_by_media()
    validate_transition_value_totals()
    plot_quaterly_sankey_by_meida()
    quaterly_change_name()



    plot_multicolumn_sankey()
