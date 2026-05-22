
import json
import pandas as pd
import os
import glob
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


def extract_txt_to_csv(input_file, output_file):
    data_list = []
    all_line = 0
    retweet_line = 0
    quote_line = 0
    reply_line = 0
    not_reply_line = 0

    with open(input_file, 'r', encoding='utf-8') as f:

        for line in f:
            all_line += 1
            if all_line % 50000 == 0:
                print(f"{input_file} processrow: {all_line} i50000output ")
            retweeted_time = None
            retweeted_id = None
            retweeted_username = None
            retweeted_user_id = None
            retweeted_user_location = None
            retweeted_full_text = None
            retweeted_hashtags = None
            retweet_time = None
            retweet_id = None
            retweet_origin_username = None
            retweet_origin_user_id = None
            retweet_origin_user_location = None
            retweet_expanded_urls_array = None
            retweet_origin_user_intro_expanded_url = None
            retweet_origin_user_des_expanded_url = None
            retweet_origin_retweet_count = None
            retweeted_origin_full_text = None
            retweet_origin_hashtags = None
            quoted_time = None
            quoted_id = None
            quoted_origin_username = None
            quoted_origin_user_id = None
            quoted_origin_user_location = None
            quoted_expanded_urls_array = None
            quoted_origin_user_intro_expanded_url = None
            quoted_origin_user_des_expanded_url = None
            quoted_origin_retweet_count = None
            quoted_origin_full_text = None
            quoted_origin_hashtags = None

            obj = json.loads(line)
            in_reply_to_status_id_str = obj.get('in_reply_to_status_id_str', None)
            if in_reply_to_status_id_str:
                reply_line += 1
            else:
                not_reply_line += 1
                retweeted_full_text = obj.get('full_text', None)
                if retweeted_full_text is not None:
                    retweeted_full_text = retweeted_full_text.replace('\r\n', ' ').replace('\n', ' ')
                retweeted_time = obj.get('created_at', None)
                retweeted_id = obj.get('id_str', None)
                retweeted_entities = obj.get('entities', None)
                if retweeted_entities:
                    retweeted_hashtags = retweeted_entities.get('hashtags', None)
                    if not retweeted_hashtags:
                        retweeted_hashtags = None
                retweeted_user = obj.get('user', None)
                if retweeted_user:
                    retweeted_user_id = retweeted_user.get('id_str', None)
                    retweeted_username = retweeted_user.get('name', None)
                    retweeted_user_location = retweeted_user.get('location', None)

                origin_retweet = obj.get('retweeted_status', None)
                if origin_retweet:
                    retweet_line += 1
                    retweet_time = origin_retweet.get('created_at', None)
                    retweet_id = origin_retweet.get('id_str', None)
                    retweeted_origin_full_text = origin_retweet.get('full_text', None)
                    if retweeted_origin_full_text is not None:
                        retweeted_origin_full_text = retweeted_origin_full_text.replace('\r\n', ' ').replace('\n', ' ')
                        # print(retweeted_origin_full_text)

                    retweet_origin_entities = origin_retweet.get('entities', None)
                    if retweet_origin_entities:
                        retweet_origin_urls = retweet_origin_entities.get('urls', None)
                        retweet_origin_hashtags = retweet_origin_entities.get('hashtags', None)
                        if not retweet_origin_hashtags:
                            retweet_origin_hashtags = None
                        if retweet_origin_urls:
                            retweet_expanded_urls_array = []
                            for url_info in retweet_origin_urls:
                                expanded_url = url_info.get('expanded_url', None)
                                if expanded_url:
                                    retweet_expanded_urls_array.append(expanded_url)

                    retweet_origin_user = origin_retweet.get('user', None)
                    if retweet_origin_user:
                        retweet_origin_user_id = retweet_origin_user.get('id_str', None)
                        retweet_origin_user_location = retweet_origin_user.get('location', None)
                        retweet_origin_user_entities = retweet_origin_user.get('entities', None)
                        retweet_origin_username = retweet_origin_user.get('name', None)

                        if retweet_origin_user_entities:
                            retweet_origin_user_intro_url = retweet_origin_user_entities.get('url', None)
                            if retweet_origin_user_intro_url:
                                retweet_origin_user_intro_urls = retweet_origin_user_intro_url.get('urls', None)
                                if retweet_origin_user_intro_urls and len(retweet_origin_user_intro_urls) > 0:
                                    retweet_origin_user_intro_expanded_url = retweet_origin_user_intro_urls[0].get(
                                        'expanded_url', None)
                                else:
                                    retweet_origin_user_intro_expanded_url = None

                            retweet_origin_user_description = retweet_origin_user_entities.get('description', None)
                            if retweet_origin_user_description:
                                retweet_origin_user_des_urls = retweet_origin_user_description.get('urls', None)
                                if retweet_origin_user_des_urls and len(retweet_origin_user_des_urls) > 0:
                                    retweet_origin_user_des_expanded_url = retweet_origin_user_des_urls[0].get(
                                        'expanded_url', None)
                                else:
                                    retweet_origin_user_des_expanded_url = None
                    retweet_origin_retweet_count = origin_retweet.get('retweet_count', None)

                origin_quoted = obj.get('quoted_status', None)
                if origin_quoted:
                    quote_line += 1
                    quoted_time = origin_quoted.get('created_at', None)
                    quoted_id = origin_quoted.get('id_str', None)
                    quoted_origin_full_text = origin_quoted.get('full_text', None)
                    if quoted_origin_full_text is not None:
                        quoted_origin_full_text = quoted_origin_full_text.replace('\r\n', ' ').replace('\n', ' ')
                        # print(quoted_origin_full_text)
                    quoted_origin_entities = origin_quoted.get('entities', None)
                    if quoted_origin_entities:
                        quoted_origin_urls = quoted_origin_entities.get('urls', None)
                        quoted_origin_hashtags = quoted_origin_entities.get('hashtags', None)
                        if not quoted_origin_hashtags:
                            quoted_origin_hashtags = None
                        if quoted_origin_urls:
                            quoted_expanded_urls_array = []
                            for url_info in quoted_origin_urls:
                                expanded_url = url_info.get('expanded_url', None)
                                if expanded_url:
                                    quoted_expanded_urls_array.append(expanded_url)

                    quoted_origin_user = origin_quoted.get('user', None)
                    if quoted_origin_user:
                        quoted_origin_user_id = quoted_origin_user.get('id_str', None)
                        quoted_origin_user_location = quoted_origin_user.get('location', None)
                        quoted_origin_user_entities = quoted_origin_user.get('entities', None)
                        quoted_origin_username = quoted_origin_user.get('name', None)

                        if quoted_origin_user_entities:
                            quoted_origin_user_intro_url = quoted_origin_user_entities.get('url', None)
                            if quoted_origin_user_intro_url:
                                quoted_origin_user_intro_urls = quoted_origin_user_intro_url.get('urls', None)
                                if quoted_origin_user_intro_urls and len(quoted_origin_user_intro_urls) > 0:
                                    quoted_origin_user_intro_expanded_url = quoted_origin_user_intro_urls[0].get(
                                        'expanded_url', None)
                                else:
                                    quoted_origin_user_intro_expanded_url = None

                            quoted_origin_user_description = quoted_origin_user_entities.get('description', None)
                            if quoted_origin_user_description:
                                quoted_origin_user_des_urls = quoted_origin_user_description.get('urls', None)
                                if quoted_origin_user_des_urls and len(quoted_origin_user_des_urls) > 0:
                                    quoted_origin_user_des_expanded_url = quoted_origin_user_des_urls[0].get(
                                        'expanded_url', None)
                                else:
                                    quoted_origin_user_des_expanded_url = None
                    quoted_origin_retweet_count = origin_quoted.get('retweet_count', None)

                # print(retweeted_origin_full_text)
                # print(quoted_origin_full_text)

                data_list.append(
                    {
                        'retweeted_time': retweeted_time,
                        'retweeted_id': retweeted_id,
                        'retweeted_user_id': retweeted_user_id,
                        'retweeted_username': retweeted_username,
                        'retweeted_user_location': retweeted_user_location,
                        'retweeted_full_text': retweeted_full_text,
                        'retweeted_hashtags': retweeted_hashtags,

                        'retweet_time': retweet_time,
                        'retweet_id': retweet_id,
                        'retweet_expanded_urls_array': retweet_expanded_urls_array,
                        'retweet_origin_user_id': retweet_origin_user_id,
                        'retweet_origin_username': retweet_origin_username,
                        'retweet_origin_user_location': retweet_origin_user_location,
                        'retweet_origin_user_intro_expanded_url': retweet_origin_user_intro_expanded_url,
                        'retweet_origin_user_des_expanded_url': retweet_origin_user_des_expanded_url,
                        'retweet_origin_retweet_count': retweet_origin_retweet_count,
                        'retweeted_origin_full_text': retweeted_origin_full_text,
                        'retweet_origin_hashtags': retweet_origin_hashtags,

                        'quoted_time': quoted_time,
                        'quoted_id': quoted_id,
                        'quoted_expanded_urls_array': quoted_expanded_urls_array,
                        'quoted_origin_user_id': quoted_origin_user_id,
                        'quoted_origin_username': quoted_origin_username,
                        'quoted_origin_user_location': quoted_origin_user_location,
                        'quoted_origin_user_intro_expanded_url': quoted_origin_user_intro_expanded_url,
                        'quoted_origin_user_des_expanded_url': quoted_origin_user_des_expanded_url,
                        'quoted_origin_retweet_count': quoted_origin_retweet_count,
                        'quoted_origin_full_text': quoted_origin_full_text,
                        'quoted_origin_hashtags': quoted_origin_hashtags,
                    })

    print(
        "-----------------------------------------------------------------------------------------------------------------------------")
    # print(data_list)

    # for i in data_list:
    #     print(i)

    print("all line:", all_line, "\tretweet_line:", retweet_line, "\tquote_line:", quote_line, "\tnot_reply_line:", not_reply_line, "\treply_line:", reply_line)

    df = pd.DataFrame(data_list, columns=[
        'retweeted_time', 'retweeted_id', 'retweeted_user_id', 'retweeted_username', 'retweeted_user_location',
        'retweeted_hashtags',
        'retweet_time', 'retweet_id', 'retweet_expanded_urls_array',
        'retweet_origin_user_id', 'retweet_origin_username', 'retweet_origin_user_location',
        'retweet_origin_user_intro_expanded_url', 'retweet_origin_user_des_expanded_url',
        'retweet_origin_retweet_count', 'retweet_origin_hashtags',
        'quoted_time', 'quoted_id', 'quoted_expanded_urls_array',
        'quoted_origin_user_id', 'quoted_origin_username', 'quoted_origin_user_location',
        'quoted_origin_user_intro_expanded_url', 'quoted_origin_user_des_expanded_url', 'quoted_origin_retweet_count',
        'quoted_origin_hashtags',
        'retweeted_full_text', 'retweeted_origin_full_text', 'quoted_origin_full_text',
    ])
    pd.set_option('expand_frame_repr', False)
    # print(df)

    df['retweet_expanded_urls_array'] = df['retweet_expanded_urls_array'].apply(
        lambda x: ', '.join(x) if isinstance(x, list) else x)
    df['quoted_expanded_urls_array'] = df['quoted_expanded_urls_array'].apply(
        lambda x: ', '.join(x) if isinstance(x, list) else x)
    df.to_csv(output_file, index=False, header=True)
    print("extract_txt_to_csv done:", input_file)

    return all_line, retweet_line, quote_line, reply_line


def batch_process_monthly_data(folder_path):
    folder_name = os.path.basename(folder_path)
    print("processingprocessfile ",folder_name)
    rp.ensure_dir(rp.DIR_01_EXTRACT_RECORD)
    record_file_path = str(rp.DIR_01_EXTRACT_RECORD / f"{folder_name}_record.txt")
    with open(record_file_path, 'w', encoding='utf-8') as record_file:
        for input_file in glob.glob(os.path.join(folder_path, '*-merged-ok.txt')):
            base_name = os.path.basename(input_file)
            print("processingprocessfile ",base_name)
            file_identifier = base_name.replace('-merged-ok.txt', '')
            out_dir = rp.ensure_dir(rp.DIR_01_PRESIDENTIAL_OUTPUT / folder_name)
            output_csv_file = str(out_dir / f"{file_identifier}-output.csv")

            all_line, retweet_line, quote_line, reply_line = extract_txt_to_csv(input_file, output_csv_file)
            print("processingcsvfilesave ", output_csv_file)
            print(f"file:{folder_path}  {input_file} -> {output_csv_file} done")
            record_file.write(f"{base_name}: all_line={all_line},retweet_line={retweet_line},quote_line={quote_line} ,reply_line={reply_line}\n")
            print("csvfilesave ", record_file_path)

def merge_all_line_retweet_line_quote_line_reply_line_record():
    rp.ensure_dir(rp.DIR_01_EXTRACT_RECORD)
    months = [
        "2019_12", "2020_01", "2020_02", "2020_03", "2020_04", "2020_05", "2020_06", "2020_07", "2020_08",
        "2020_09", "2020_10", "2020_11", "2020_12", "2021_01", "2021_02",
    ]
    file_names = [
        str(rp.DIR_01_EXTRACT_RECORD / f"merge_{m}_record.txt")
        for m in months
        if (rp.DIR_01_EXTRACT_RECORD / f"merge_{m}_record.txt").is_file()
    ]
    if not file_names:
        print("[merge_all_line]  merge_*_record.txt skip ")
        return
    with open(rp.DIR_01_EXTRACT_RECORD / "summary_merge_all_months_record.txt", "w", encoding="utf-8") as summary_file:
        for file_name in file_names:
            if not os.path.isfile(file_name):
                continue
            all_line_sum = 0
            retweet_line_sum = 0
            quote_line_sum = 0
            reply_line_sum = 0

            with open(file_name, 'r') as file:
                for line in file:
                    parts = line.split(',')
                    for part in parts:
                        if 'all_line' in part:
                            all_line_sum += int(part.split('=')[1])
                        elif 'retweet_line' in part:
                            retweet_line_sum += int(part.split('=')[1])
                        elif 'quote_line' in part:
                            quote_line_sum += int(part.split('=')[1])
                        elif 'reply_line' in part:
                            reply_line_sum += int(part.split('=')[1])

            summary_file.write(
                f"{file_name}: all_line={all_line_sum}, retweet_line={retweet_line_sum}, quote_line={quote_line_sum}, reply_line={reply_line_sum}\n")

def final_result_all_line_retweet_line_quote_line_reply_line_output_to_terminal():
    file_name = str(rp.DIR_01_EXTRACT_RECORD / "summary_merge_all_months_record.txt")
    all_line_sum = 0
    retweet_line_sum = 0
    quote_line_sum = 0
    reply_line_sum = 0
    with open(file_name, 'r') as file:
        for line in file:
            parts = line.split(',')
            for part in parts:
                if 'all_line' in part:
                    all_line_sum += int(part.split('=')[1])
                elif 'retweet_line' in part:
                    retweet_line_sum += int(part.split('=')[1])
                elif 'quote_line' in part:
                    quote_line_sum += int(part.split('=')[1])
                elif 'reply_line' in part:
                    reply_line_sum += int(part.split('=')[1])

        print(f"all_line: {all_line_sum}")
        print(f"retweet_line: {retweet_line_sum}")
        print(f"quote_line: {quote_line_sum}")
        print(f"reply_line: {reply_line_sum}")


if __name__ == "__main__":
    demo_merge = rp.DIR_01 / "merge_2019_12"
    if demo_merge.is_dir():
        batch_process_monthly_data(str(demo_merge))
    else:
        print("[info]  01 processdata/merge_2019_12 skip batch_process_monthly_data ")
    # merge_all_line_retweet_line_quote_line_reply_line_record()
    # final_result_all_line_retweet_line_quote_line_reply_line_output_to_terminal()