import os
import sys
import re
from glob import glob
from pathlib import Path
from urllib.parse import urlparse

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


def extract_domain_external(url):
    """Project workflow helper."""
    if pd.isna(url):
        return None

    url_str = str(url).strip("[]'\" ")
    if "," in url_str:
        url_str = url_str.split(",")[0].strip(" '\"")

    if not url_str.startswith(("http://", "https://")):
        url_str = "http://" + url_str

    try:
        parsed = urlparse(url_str)
        domain = parsed.netloc
        if ":" in domain:
            domain = domain.split(":")[0]
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.lower().strip()
    except Exception:
        return None


def process_month_external(directory, media_url_domain):
    media_domain_set = set(media_url_domain)
    output_files = glob(os.path.join(directory, "****-**-**-*-output.csv"))
    df_list = []
    print(f"processfile: {directory}  {len(output_files)} file")

    for file in output_files:
        try:
            df = pd.read_csv(file, dtype=str)
            df["retweet_domain"] = df["retweet_expanded_urls_array"].apply(extract_domain_external)
            df["quote_domain"] = df["quoted_expanded_urls_array"].apply(extract_domain_external)

            is_rt_match = df["retweet_domain"].isin(media_domain_set)
            is_qt_match = df["quote_domain"].isin(media_domain_set)
            mask = is_rt_match | is_qt_match
            if not mask.any():
                continue

            sub_df = df[mask].copy()
            sub_rt_match = sub_df["retweet_domain"].isin(media_domain_set)
            sub_qt_match = sub_df["quote_domain"].isin(media_domain_set)
            condition_use_quote = (~sub_rt_match) & sub_qt_match

            sub_df.loc[condition_use_quote, "retweet_origin_user_id"] = sub_df.loc[
                condition_use_quote, "quoted_origin_user_id"
            ]
            sub_df.loc[condition_use_quote, "retweet_origin_username"] = sub_df.loc[
                condition_use_quote, "quoted_origin_username"
            ]
            sub_df["matched_domain"] = sub_df["retweet_domain"].where(
                sub_rt_match, sub_df["quote_domain"]
            )

            cols = [
                "retweeted_user_id",
                "retweeted_username",
                "retweet_origin_user_id",
                "retweet_origin_username",
                "matched_domain",
            ]
            valid_cols = [c for c in cols if c in sub_df.columns]
            df_list.append(sub_df[valid_cols])
        except Exception as e:
            print(f"processfile {os.path.basename(file)} : {e}")

    dir_name = Path(directory).name
    save_dir = rp.SIMPLIFIED_FORWARDING_MEDIA_EXTERNAL
    rp.ensure_dir(save_dir)
    output_path = save_dir / f"{dir_name}.csv"

    if df_list:
        matching_media_df = pd.concat(df_list, ignore_index=True)
        matching_media_df.to_csv(output_path, index=False)
        print(f"savemediainformation: {output_path}")
        print(f"data: {len(matching_media_df)} ")
    else:
        empty_df = pd.DataFrame(
            columns=[
                "retweeted_user_id",
                "retweeted_username",
                "retweet_origin_user_id",
                "retweet_origin_username",
                "matched_domain",
            ]
        )
        empty_df.to_csv(output_path, index=False)
        print(f"directorydata savefile: {output_path}")


def build_media_simplified_forwarding_external_main():
    directory = rp.THREE_PARTS_OUTPUT / "external_url"

    print("processingmedia...")
    combined_df = pd.read_csv(rp.MEDIA_BIAS_URL_CSV, dtype=str)
    political_leanings_df = combined_df.dropna(subset=["bias"])
    media_url_domain = set(political_leanings_df["domain"].apply(extract_domain_external))
    print(f"media  {len(media_url_domain)}  ")

    for k in range(2019, 2022):
        for j in range(1, 13):
            if k == 2019 and j < 12:
                continue
            if k == 2021 and j > 2:
                continue

            month = str(j).zfill(2)
            folder = f"output_{k}_{month}"
            folder_path = directory / folder

            if folder_path.exists():
                print(f"\n>>> processfile: {folder_path}")
                process_month_external(str(folder_path), media_url_domain)
            else:
                print(f"skipfile: {folder_path}")


def extract_domain_twitter(url):
    """Project workflow helper."""
    if pd.isna(url):
        return None

    url_str = str(url).strip("[]'\" ")
    if "," in url_str:
        url_str = url_str.split(",")[0].strip(" '\"")

    if not url_str.startswith(("http://", "https://")):
        url_str = "http://" + url_str

    try:
        parsed = urlparse(url_str)
        path_segments = parsed.path.split("/")
        if len(path_segments) > 1:
            return path_segments[1].strip()
        return None
    except Exception:
        return None


def process_month_twitter(directory, media_username_set):
    media_set = set(media_username_set)
    output_files = glob(os.path.join(directory, "****-**-**-*-output.csv"))
    df_list = []
    print(f"process Twitter file: {directory}  {len(output_files)} file")

    for file in output_files:
        try:
            df = pd.read_csv(file, dtype=str)
            df["retweet_domain"] = df["retweet_expanded_urls_array"].apply(extract_domain_twitter)
            df["quote_domain"] = df["quoted_expanded_urls_array"].apply(extract_domain_twitter)

            is_rt_match = df["retweet_domain"].isin(media_set)
            is_qt_match = df["quote_domain"].isin(media_set)
            mask = is_rt_match | is_qt_match
            if not mask.any():
                continue

            sub_df = df[mask].copy()
            sub_rt_match = sub_df["retweet_domain"].isin(media_set)
            sub_qt_match = sub_df["quote_domain"].isin(media_set)
            condition_use_quote = (~sub_rt_match) & sub_qt_match

            sub_df.loc[condition_use_quote, "retweet_origin_user_id"] = sub_df.loc[
                condition_use_quote, "quoted_origin_user_id"
            ]
            sub_df.loc[condition_use_quote, "retweet_origin_username"] = sub_df.loc[
                condition_use_quote, "quoted_origin_username"
            ]
            sub_df["matched_domain"] = sub_df["retweet_domain"].where(
                sub_rt_match, sub_df["quote_domain"]
            )

            cols = [
                "retweeted_user_id",
                "retweeted_username",
                "retweet_origin_user_id",
                "retweet_origin_username",
                "matched_domain",
            ]
            valid_cols = [c for c in cols if c in sub_df.columns]
            df_list.append(sub_df[valid_cols])
        except Exception as e:
            print(f"processfile {os.path.basename(file)} : {e}")

    dir_name = Path(directory).name
    save_dir = rp.SIMPLIFIED_FORWARDING_MEDIA_TWITTER
    rp.ensure_dir(save_dir)
    output_path = save_dir / f"{dir_name}.csv"

    if df_list:
        matching_media_df = pd.concat(df_list, ignore_index=True)
        matching_media_df.to_csv(output_path, index=False)
        print(f"save Twitter information: {output_path}")
        print(f"data: {len(matching_media_df)} ")
    else:
        empty_df = pd.DataFrame(
            columns=[
                "retweeted_user_id",
                "retweeted_username",
                "retweet_origin_user_id",
                "retweet_origin_username",
                "matched_domain",
            ]
        )
        empty_df.to_csv(output_path, index=False)
        print(f"directorydata savefile: {output_path}")


def build_media_simplified_forwarding_twitter_main():
    directory = rp.THREE_PARTS_OUTPUT / "twitter_url"

    print("processing Twitter user...")
    combined_df = pd.read_csv(rp.MEDIA_BIAS_USERNAME_CSV, dtype=str)
    political_leanings_df = combined_df.dropna(subset=["bias"])
    media_username_set = set(political_leanings_df["Username"].str.strip())
    print(f"Twitter user  {len(media_username_set)} user ")

    for k in range(2019, 2022):
        for j in range(1, 13):
            if k == 2019 and j < 12:
                continue
            if k == 2021 and j > 2:
                continue

            month = str(j).zfill(2)
            folder = f"output_{k}_{month}"
            folder_path = directory / folder

            if folder_path.exists():
                print(f"\n>>> processfile: {folder_path}")
                process_month_twitter(str(folder_path), media_username_set)
            else:
                print(f"skipfile: {folder_path}")


def extract_domain_without(user_id_str):
    """Project workflow helper."""
    if pd.isna(user_id_str):
        return None
    clean_id = str(user_id_str).strip()
    return clean_id if clean_id else None


def process_month_without(directory, media_userid_set):
    media_set = set(media_userid_set)
    output_files = glob(os.path.join(directory, "****-**-**-*-output.csv"))
    df_list = []
    print(f"process Without file: {directory}  {len(output_files)} file")

    for file in output_files:
        try:
            df = pd.read_csv(file, dtype=str)
            df["retweet_domain"] = df["retweet_origin_user_id"].apply(extract_domain_without)
            df["quote_domain"] = df["quoted_origin_user_id"].apply(extract_domain_without)

            is_rt_match = df["retweet_domain"].isin(media_set)
            is_qt_match = df["quote_domain"].isin(media_set)
            mask = is_rt_match | is_qt_match
            if not mask.any():
                continue

            sub_df = df[mask].copy()
            sub_rt_match = sub_df["retweet_domain"].isin(media_set)
            sub_qt_match = sub_df["quote_domain"].isin(media_set)
            condition_use_quote = (~sub_rt_match) & sub_qt_match

            sub_df.loc[condition_use_quote, "retweet_origin_user_id"] = sub_df.loc[
                condition_use_quote, "quoted_origin_user_id"
            ]
            sub_df.loc[condition_use_quote, "retweet_origin_username"] = sub_df.loc[
                condition_use_quote, "quoted_origin_username"
            ]
            sub_df["matched_domain"] = sub_df["retweet_domain"].where(
                sub_rt_match, sub_df["quote_domain"]
            )

            cols = [
                "retweeted_user_id",
                "retweeted_username",
                "retweet_origin_user_id",
                "retweet_origin_username",
                "matched_domain",
            ]
            valid_cols = [c for c in cols if c in sub_df.columns]
            df_list.append(sub_df[valid_cols])
        except Exception as e:
            print(f"processfile {os.path.basename(file)} : {e}")

    dir_name = Path(directory).name
    save_dir = rp.SIMPLIFIED_FORWARDING_MEDIA_WITHOUT
    rp.ensure_dir(save_dir)
    output_path = save_dir / f"{dir_name}.csv"

    if df_list:
        matching_media_df = pd.concat(df_list, ignore_index=True)
        matching_media_df.to_csv(output_path, index=False)
        print(f"save Without information: {output_path}")
        print(f"data: {len(matching_media_df)} ")
    else:
        empty_df = pd.DataFrame(
            columns=[
                "retweeted_user_id",
                "retweeted_username",
                "retweet_origin_user_id",
                "retweet_origin_username",
                "matched_domain",
            ]
        )
        empty_df.to_csv(output_path, index=False)
        print(f"directorydata savefile: {output_path}")


def build_media_simplified_forwarding_without_main():
    directory = rp.THREE_PARTS_OUTPUT / "without_url"

    print("processing mediaID ...")
    try:
        combined_df = pd.read_csv(rp.MEDIA_BIAS_USERNAME_CSV, dtype=str)
        combined_df.columns = combined_df.columns.str.strip().str.lower()
        print(f"filecolumn: {combined_df.columns.tolist()}")

        if "bias" not in combined_df.columns:
            print("error CSVfile 'bias' column ")
            return
        if "id_str" not in combined_df.columns:
            print("error CSVfile 'id_str' column  ")
            return

        political_leanings_df = combined_df.dropna(subset=["bias"])
        media_userid_set = set(political_leanings_df["id_str"].str.strip())
        print(f"mediaID  {len(media_userid_set)} ID ")

        for k in range(2019, 2022):
            for j in range(1, 13):
                if k == 2019 and j < 12:
                    continue
                if k == 2021 and j > 2:
                    continue

                month = str(j).zfill(2)
                folder = f"output_{k}_{month}"
                folder_path = directory / folder

                if folder_path.exists():
                    print(f"\n>>> processfile: {folder_path}")
                    process_month_without(str(folder_path), media_userid_set)
                else:
                    print(f"skipfile: {folder_path}")
    except Exception as e:
        print(f"error: {e}")


if __name__ == "__main__":
    build_media_simplified_forwarding_external_main()
    build_media_simplified_forwarding_twitter_main()
    build_media_simplified_forwarding_without_main()
