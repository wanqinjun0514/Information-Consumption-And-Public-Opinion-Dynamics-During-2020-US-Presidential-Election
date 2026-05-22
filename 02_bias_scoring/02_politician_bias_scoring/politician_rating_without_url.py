import pandas as pd
import os
from tqdm import tqdm
import sys
from pathlib import Path

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

def get_bias_dict():
    """Project workflow helper."""
    file_path = str(rp.POLITICIAN_USERNAME_CSV)
    df = pd.read_csv(file_path, dtype=str)
    user_id_col = df.iloc[:, 0]
    bias_col = df.iloc[:, 1].map({'Left': -1, 'Right': 1, 'Center': 0}).dropna()
    return dict(zip(user_id_col, bias_col))


def extract_monthly_politician_influence_without_url(value_map):
    months = ['2019_12', '2020_01', '2020_02', '2020_03', '2020_04', '2020_05', '2020_06', '2020_07', '2020_08',
              '2020_09', '2020_10', '2020_11', '2020_12', '2021_01', '2021_02']
    for month in months:
        # Example usage
        input_folder = str(rp.THREE_PARTS_OUTPUT / "without_url" / f"output_{month}")
        if not os.path.isdir(input_folder):
            print(f"skip directory : {input_folder}")
            continue
        output_folder = str(rp.DIR_02_OUTPUTS / "politician_influence" / "without_url")
        statistic_results_file = str(Path(output_folder) / f"simplified_forwarding_stats_{month}.csv")

        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)

        # Prepare output file path
        output_file_path = os.path.join(output_folder, rf'politician_influence_output_{month}.csv')

        # Prepare the list to store the extracted rows
        result_data = []
        total_retweet_count = 0
        total_quote_count = 0
        summary_data = []
        # Loop through all files in the input folder
        for file_name in os.listdir(input_folder):
            if file_name.endswith('-output.csv'):
                file_path = os.path.join(input_folder, file_name)
                # Read the csv file
                df = pd.read_csv(file_path, dtype=str)
                print('processingreadfile:', file_path)
                retweet_count = 0
                quote_count = 0
                if len(df.columns) >= 20:
                    # Loop through each row
                    for index, row in df.iterrows():
                        # Check if the row has enough columns
                        if len(row) >= 20:
                            retweeted_user_id = row.iloc[2]  # 3rd column
                            retweet_origin_user_id = row.iloc[9]  # 10th column
                            quote_origin_user_id = row.iloc[19]  # 20th column

                            # Check if either 10th or 20th column is in the value_map
                            if (retweet_origin_user_id in value_map) or (quote_origin_user_id in value_map):
                                # Determine which one is not empty for retweet_or_quote_origin_user_id
                                retweet_or_quote_origin_user_id = retweet_origin_user_id if pd.notna(retweet_origin_user_id) else quote_origin_user_id
                                bias_value = value_map[retweet_or_quote_origin_user_id]
                                # Increment retweet or quote count
                                if retweet_origin_user_id in value_map:
                                    retweet_count += 1
                                if quote_origin_user_id in value_map:
                                    quote_count += 1
                                # Append to result list
                                result_data.append({
                                    'retweeted_user_id': retweeted_user_id,
                                    'retweet_or_quote_origin_user_id': retweet_or_quote_origin_user_id,
                                    'bias_value': bias_value
                                })
                else:
                    print(f"Skipping file {file_name} because it doesn't have enough columns.")
                # Print the retweet and quote counts
                print(f"file {file_path}politician: {retweet_count}")
                print(f"file {file_path}politician {quote_count}")
                retweet_and_quote_count = retweet_count + quote_count
                print(f"file {file_path}politician {retweet_and_quote_count}")
                total_retweet_count += retweet_count
                total_quote_count += quote_count
                summary_data.append({
                    'file_name': file_path,
                    'retweet_count': retweet_count,
                    'quote_count': quote_count,
                    'retweet_and_quote_count': retweet_and_quote_count
                })
        print(f"{input_folder}pathfilepolitician: {total_retweet_count}")
        print(f"{input_folder}pathfilepolitician {total_quote_count}")
        total_count = total_retweet_count + total_quote_count
        print(f"{input_folder}pathfilepolitician {total_count}")
        statistic_results_df = pd.DataFrame(summary_data)
        statistic_results_df.to_csv(statistic_results_file, index=False)
        print(f"savepoliticianinformationsummarydata {statistic_results_file}")
        # Convert the result list to a DataFrame and save as CSV
        if result_data:
            result_df = pd.DataFrame(result_data)
            result_df.to_csv(output_file_path, index=False, columns=['retweeted_user_id', 'retweet_or_quote_origin_user_id', 'bias_value'])
        else:
            print(f"[info] {month} politician/ generate {output_file_path}")

def calculate_monthly_user_bias_from_simplified_forwarding():
    months = ['2019_12', '2020_01', '2020_02', '2020_03', '2020_04', '2020_05', '2020_06', '2020_07', '2020_08',
              '2020_09', '2020_10', '2020_11', '2020_12', '2021_01', '2021_02']
    for month in months:
        inf_dir = Path(rp.DIR_02_OUTPUTS) / "politician_influence" / "without_url"
        file_path = str(inf_dir / f"politician_influence_output_{month}.csv")
        if not os.path.isfile(file_path):
            print(f"[info] skip {month} missingfile row : {file_path}")
            continue
        df = pd.read_csv(file_path,
                         dtype={'retweeted_user_id': str, 'retweet_or_quote_origin_user_id': str, 'bias_value': float})
        print('processingprocessfile ', file_path)
        total_bias_points_dict = {}
        retweet_times_dict = {}
        for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing rows"):
            retweeted_user_id = row['retweeted_user_id']
            bias_value = row['bias_value']
            if retweeted_user_id in total_bias_points_dict:
                total_bias_points_dict[retweeted_user_id] += bias_value
            else:
                total_bias_points_dict[retweeted_user_id] = bias_value
            if retweeted_user_id in retweet_times_dict:
                retweet_times_dict[retweeted_user_id] += 1
            else:
                retweet_times_dict[retweeted_user_id] = 1


        total_retweet_times = sum(retweet_times_dict.values())
        print(f"Retweet times total: {total_retweet_times}")
        result_data = []
        for retweeted_user_id in total_bias_points_dict:
            total_bias_points = total_bias_points_dict[retweeted_user_id]
            retweet_times = retweet_times_dict[retweeted_user_id]
            average_bias_points = total_bias_points / retweet_times
            result_data.append({
                'retweeted_user_id': retweeted_user_id,
                'total_bias_points': total_bias_points,
                'retweet_times': retweet_times,
                'average_bias_points': average_bias_points
            })
        result_df = pd.DataFrame(result_data)
        out_dir = rp.ensure_dir(rp.DIR_02_POLITICIAN_RATING_ROOT / "without_url-rating" / "monthly_users_bias")
        output_file = str(out_dir / f"{month}_output.csv")
        result_df.to_csv(output_file, index=False)
        print(f"processsave {output_file}")


if __name__ == '__main__':
    bias_dict = get_bias_dict()
    extract_monthly_politician_influence_without_url(bias_dict)
    calculate_monthly_user_bias_from_simplified_forwarding()
