import os
import sys
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd
import logging

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



def build_url_score_dict(file_path):
    df = pd.read_csv(file_path, header=0, dtype=str, index_col=False)
    if "Url" not in df.columns and "domain" in df.columns:
        df = df.rename(columns={"domain": "Url"})
    if "Url" not in df.columns:
        raise ValueError(f"mediabiasmissing Url/domain column: {file_path}")

    bias_mapping = {
        'Extreme Bias Right': 3,
        'Right': 2,
        'Right Leaning': 1,
        'Center': 0,
        'Left Leaning': -1,
        'Left': -2,
        'Extreme Bias Left': -3,
        'Fake News': 3,
    }
    bias_mapping_lower = {k.lower(): v for k, v in bias_mapping.items()}
    # print(df)
    bias_counts = df['bias'].value_counts()

    print("Bias Category Counts in CSV:")
    for bias, count in bias_counts.items():
        print(f"{bias}: {count} entries")
    df["score"] = (
        df["bias"].astype(str).str.strip().str.lower().map(bias_mapping_lower).fillna(0).astype(int)
    )

    print(df)

    url_score = dict(zip(df['Url'].str.strip(), df['score']))
    score_counts = pd.Series(url_score.values()).value_counts()

    print("Bias Category Counts in url_score Dictionary:")
    for score, count in score_counts.items():
        bias_category = [k for k, v in bias_mapping.items() if v == score]
        if bias_category:
            print(f"{bias_category[0]} (score {score}): {count} entries")
        else:
            print(f"Unmapped score {score}: {count} entries")
    return url_score


def extract_url(url):
    try:
        return urlparse(url).netloc
    except Exception as e:
        return None


def user_bias_by_external_url():
    user_bias_score = {}
    user_appearance_count = {}
    url_score_file_path = str(rp.MEDIA_BIAS_URL_CSV)
    url_score = build_url_score_dict(url_score_file_path)
    # print(url_score)

    months = ['2019_12', '2020_01', '2020_02', '2020_03', '2020_04', '2020_05', '2020_06', '2020_07', '2020_08',
              '2020_09', '2020_10', '2020_11', '2020_12', '2021_01', '2021_02', ]

    for month in months:
        print(
            f"{month}=========================================================================================================")
        every_mouth_retweet_url_num = 0
        every_mouth_quoted_url_num = 0
        every_mouth_other_num = 0
        every_mouth_retweet_url_have_soure_num = 0
        every_mouth_quoted_url_have_num = 0
        user_bias_score = {}
        user_appearance_count = {}
        folder_path = str(rp.THREE_PARTS_OUTPUT / "external_url" / f"output_{month}")
        if not os.path.isdir(folder_path):
            print(f"skip directory : {folder_path}")
            continue
        for filename in os.listdir(folder_path):
            if filename.endswith("-output.csv"):
                # print(folder_path)
                # print(filename)
                file_path = os.path.join(folder_path, filename)
                # print(file_path)
                df = pd.read_csv(file_path, usecols=['retweeted_user_id', 'retweet_expanded_urls_array',
                                                     'quoted_expanded_urls_array'],
                                 dtype={'retweeted_user_id': 'str', 'retweet_expanded_urls_array': 'str',
                                        'quoted_expanded_urls_array': 'str'})
                # print(df)
                print('processingprocess ', file_path)

                for index, row in df.iterrows():
                    user_id = row['retweeted_user_id']
                    retweet_url = row['retweet_expanded_urls_array']
                    quoted_url = row['quoted_expanded_urls_array']

                    if pd.notna(retweet_url):
                        # print(f"{user_id}   1")
                        every_mouth_retweet_url_num += 1
                        domain = extract_url(retweet_url)
                        score = url_score.get(domain)

                        if score is not None:
                            every_mouth_retweet_url_have_soure_num += 1
                            if user_id in user_bias_score:
                                user_bias_score[user_id] += score
                                user_appearance_count[user_id] += 1
                            else:
                                user_bias_score[user_id] = score
                                user_appearance_count[user_id] = 1
                    elif pd.notna(quoted_url):
                        # print(f"{user_id}   2")
                        every_mouth_quoted_url_num += 1
                        domain = extract_url(quoted_url)
                        score = url_score.get(domain)

                        if score is not None:
                            every_mouth_quoted_url_have_num += 1
                            if user_id in user_bias_score:
                                user_bias_score[user_id] += score
                                user_appearance_count[user_id] += 1
                            else:
                                user_bias_score[user_id] = score
                                user_appearance_count[user_id] = 1
                    else:
                        # print(f"{user_id}   3")
                        every_mouth_other_num += 1

        print(
            f"retweet_url_num:{every_mouth_retweet_url_num}\tquoted_url_num:{every_mouth_quoted_url_num}\tother_num:{every_mouth_other_num}"
            f"every_mouth_retweet_url_have_soure_num:{every_mouth_retweet_url_have_soure_num}\tevery_mouth_quoted_url_have_num:{every_mouth_quoted_url_have_num}")

        logging.basicConfig(filename='media bias.log', level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

        log_message = (
            f"retweet_url_num:{every_mouth_retweet_url_num}\tquoted_url_num:{every_mouth_quoted_url_num}\tother_num:{every_mouth_other_num}"
            f"every_mouth_retweet_url_have_soure_num:{every_mouth_retweet_url_have_soure_num}\tevery_mouth_quoted_url_have_num:{every_mouth_quoted_url_have_num}")

        logging.info(log_message)

        user_stats = pd.DataFrame({
            'user_id': list(user_bias_score.keys()),
            'total_score': list(user_bias_score.values()),
            'appearance_count': list(user_appearance_count.values())
        })
        user_stats["average_bias_points"] = user_stats["total_score"] / user_stats[
            "appearance_count"
        ].replace(0, pd.NA)
        print(user_stats)

        out_dir = rp.ensure_dir(rp.DIR_02_MEDIA_RATING_ROOT / "external_url-rating")
        output_path = str(out_dir / f"user_bias_scores_{month}.csv")

        user_stats.to_csv(output_path, index=False)


if __name__ == "__main__":
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    user_bias_by_external_url()
