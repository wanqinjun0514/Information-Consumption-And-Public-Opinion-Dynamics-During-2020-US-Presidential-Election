
import pandas as pd
import sys
from pathlib import Path

_rp = Path(__file__).resolve()
for _ in range(8):
    if (_rp / "repo_paths.py").exists():
        if str(_rp) not in sys.path:
            sys.path.insert(0, str(_rp))
        break
    _rp = _rp.parent
import repo_paths as rp

MID = rp.DIR_03_COEXPOSURE_INTERMEDIATE
def calculate_common_user_proportion():
    file_path = str(MID / "politician_common_influenced_users_sorted_top_7326rows.csv")
    df = pd.read_csv(file_path)

    total_common_user_count = df['common_user_count'].sum()

    df['common_user_proportion'] = df['common_user_count'] / total_common_user_count

    output_file_path = str(MID / "politician_common_influenced_users_with_proportion_top_7326rows.csv")
    df.to_csv(output_file_path, index=False)

    print("Data processing complete. The new file has been saved.")


def find_threshold_row():
    file_path = str(MID / "politician_common_influenced_users_sorted.csv")
    df = pd.read_csv(file_path)

    total_common_user_count = df['common_user_count'].sum()

    threshold_value = 0.6 * total_common_user_count

    cumulative_sum = 0
    threshold_row = -1
    for index, count in enumerate(df['common_user_count']):
        cumulative_sum += count
        if cumulative_sum >= threshold_value:
            threshold_row = index + 1
            break

    print(f"The threshold row is: {threshold_row}")

def drop_count_column():
    file_path = str(MID / "politician_top_7326rows_edge_list.csv")
    df = pd.read_csv(file_path)

    df = df.drop(columns=['count'])

    output_file_path = str(MID / "politician_top_7326rows_edge_list_no_count.csv")
    df.to_csv(output_file_path, index=False)

    print("Column 'count' has been removed and the new file has been saved.")

def extract_unique_source_target_ids():
    file_path = str(MID / "politician_top_7326rows_edge_list_no_count.csv")
    df = pd.read_csv(file_path)

    unique_nodes = set(df['source']).union(set(df['target']))

    output_df = pd.DataFrame({'id': list(unique_nodes)})
    output_file_path = str(MID / "politician_unique_nodes.csv")
    output_df.to_csv(output_file_path, index=False)

    print("Unique nodes have been extracted and saved to the new file.")


def attach_bias_to_ids():
    nodes_file_path = str(MID / "politician_unique_nodes.csv")
    nodes_df = pd.read_csv(nodes_file_path)

    bias_file_path = str(MID / "combined with screenname and bias.csv")
    bias_df = pd.read_csv(bias_file_path)

    merged_df = nodes_df.merge(bias_df[['retweet_origin_user_id', 'bias']], left_on='id',
                               right_on='retweet_origin_user_id', how='left')

    merged_df = merged_df[['id', 'bias']].rename(columns={'bias': 'label'})

    merged_df = merged_df.sort_values(by='id')

    output_file_path = str(MID / "politician_nodes_with_bias.csv")
    merged_df.to_csv(output_file_path, index=False)
    print("Bias information has been added and the new file has been saved.")




if __name__ == '__main__':
    # calculate_common_user_proportion()
    # drop_count_column()
    # extract_unique_source_target_ids()
    attach_bias_to_ids()