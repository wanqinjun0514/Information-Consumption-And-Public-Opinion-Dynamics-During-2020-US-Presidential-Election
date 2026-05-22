import json
import os
import shutil
import tempfile
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


def delete_bad_txt(directory, record_path):
    for filename in os.listdir(directory):
        if filename.endswith("-bad.txt"):
            file_path = os.path.join(directory, filename)
            os.remove(file_path)
            with open(record_path, 'a', encoding='utf-8') as f_delete:
                f_delete.write(f"Deleted: {file_path}\n")
            print(f"Deleted: {file_path}")


def check_and_remove_invalid_lines(txt_source_path, error_record_path):
    temp_file_path = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8').name
    temp_dir = tempfile.gettempdir()
    print("Temporary file path:", temp_dir)

    line_number = 0
    true_count = 0
    error_count = 0
    null_count = 0
    has_error = False

    with (open(txt_source_path, 'r', encoding='utf-8') as source_file,
          open(temp_file_path, 'w', encoding='utf-8') as temp_file,
          open(error_record_path, 'a', encoding='utf-8') as error_file):
        for line in source_file:
            line_number += 1
            try:
                json.loads(line)
                temp_file.write(line)
                true_count += 1
            except json.JSONDecodeError:
                print(f"row {line_number}: {line.strip()} \n  JSON data ")
                error_file.write(line.strip() + '\n')
                error_count += 1
                has_error = True
            except Exception as e:
                if not line.strip():
                    print(f"row {line_number}: row  ")
                    null_count += 1
                    continue
                else:
                    print(f"row {line_number}: {line.strip()} \n : {e}")
                    has_error = True

    if has_error:
        shutil.move(temp_file_path, txt_source_path)
        print(f"errorrow {true_count}")
        print(f"errorrow errorrow {error_count}")
        print(f"row errorrow {null_count}")

    else:
        print("row JSON data file ")
        temp_file.close()
        os.remove(temp_file_path)

    return true_count, error_count, null_count


def batch_check_and_remove_invalid_lines(source_txt_directory, record_json_path, error_txt_path):
    for filename in os.listdir(source_txt_directory):
        print(
            "-----------------------------------------------------------------------------------------------------------")
        print(filename)
        true_count, error_count, null_count = check_and_remove_invalid_lines(
            os.path.join(source_txt_directory, filename), error_txt_path)
        print(f"row {true_count}\terrorrow {error_count}\trow {null_count}\n")

        with open(record_json_path, 'a', encoding='utf-8') as f_batch_check:
            f_batch_check.write(f"{filename}: row {true_count}\t\terrorrow {error_count}\t\trow {null_count}\n")


def merge_source_json_line(source_txt_directory_path, merge_txt_directory_path, record_txt_path_merge):
    files_by_date = {}

    for filename in os.listdir(source_txt_directory_path):
        if filename.startswith('us-presidential-tweet-id') and filename.endswith('ok.txt'):
            date = '-'.join(filename.split('-')[4:7])
            if date not in files_by_date:
                files_by_date[date] = []
            files_by_date[date].append(filename)

    for key, value in files_by_date.items():
        print(f"{key}: ", end='')
        for i, filename in enumerate(value, 1):
            end_char = '\n\t\t\t' if i % 3 == 0 else ', '
            print(filename, end=end_char)
        print()
    with open(record_txt_path_merge, 'a', encoding='utf-8') as f_merge_01:
        for key, value in files_by_date.items():
            f_merge_01.write(f"{key}: ")
            for i, filename in enumerate(value, 1):
                end_char = '\n\t\t   ' if i % 3 == 0 else ', '
                f_merge_01.write(f"{filename}{end_char}")
            f_merge_01.write("\n")

    for date, filenames in files_by_date.items():
        sorted_filenames = sorted(filenames)
        lines_written = 0
        file_counter = 1
        output_file = None

        for filename in sorted_filenames:
            being_processed_txt = os.path.join(source_txt_directory_path, filename)
            print(f"being_processed:  {being_processed_txt}")
            with open(being_processed_txt, 'r', encoding='utf-8') as f:
                for line in f:
                    if lines_written == 500000 or lines_written == 0:
                        if output_file:
                            output_file.close()
                            print(
                                "--------------------------------------------------------------------------------------------")
                            print(f"close merge txt: {output_filename}\tnum_line: {lines_written}")
                            with open(record_txt_path_merge, 'a', encoding='utf-8') as f_merge_02:
                                f_merge_02.write(f"merge txt: {output_filename}\tnum_line: {lines_written}\n")
                            print(
                                "--------------------------------------------------------------------------------------------")
                        output_filename = f"{date}-{file_counter}-merged-ok.txt"
                        print(
                            "--------------------------------------------------------------------------------------------")
                        print(f"create merge txt: {output_filename}")
                        print(
                            "--------------------------------------------------------------------------------------------")

                        output_file = open(os.path.join(merge_txt_directory_path, output_filename), 'w', encoding='utf-8')
                        file_counter += 1
                        lines_written = 0
                    output_file.write(line)
                    lines_written += 1
            print(f"close source txt: {being_processed_txt}")

        if output_file:
            output_file.close()
            print("--------------------------------------------------------------------------------------------")
            print(f"close merge txt: {output_filename}\tnum_line: {lines_written}")
            with open(record_txt_path_merge, 'a', encoding='utf-8') as f_merge_02:
                f_merge_02.write(f"merge txt: {output_filename}\tnum_line: {lines_written}\n")
            print("--------------------------------------------------------------------------------------------")


def wash_json(record_txt_path, merge_directory_path, source_directory_path, error_json_path):
    print("Deleted:'-bad.txt'")
    print("-----------------------------------------------------------------------------------------------------------")
    with open(record_txt_path, 'a', encoding='utf-8') as file:
        file.write(f"Deleted:'-bad.txt'\n")
    delete_bad_txt(source_directory_path, record_txt_path)

    print("===========================================================================================================")
    with open(record_txt_path, 'a', encoding='utf-8') as file:
        file.write(
            f"-----------------------------------------------------------------------------------------------------------\n")

    print("check_and_remove_invalid_json")
    with open(record_txt_path, 'a', encoding='utf-8') as file:
        file.write(f"check_and_remove_invalid_json:\n")
    batch_check_and_remove_invalid_lines(source_directory_path, record_txt_path, error_json_path)

    print("===========================================================================================================")
    with open(record_txt_path, 'a', encoding='utf-8') as file:
        file.write(
            f"-----------------------------------------------------------------------------------------------------------\n")

    print("Merge same date txt")
    print("-----------------------------------------------------------------------------------------------------------")
    with open(record_txt_path, 'a', encoding='utf-8') as file:
        file.write(f"Merge same date txt:\n")
    merge_source_json_line(source_directory_path, merge_directory_path, record_txt_path)


if __name__ == "__main__":
    demo = rp.DIR_01 / "wash_demo" / "2020_08"
    rp.ensure_dir(demo / "raw_json")
    rp.ensure_dir(demo / "merge_out")
    wash_json(
        str(demo / "record_2020_08.txt"),
        str(demo / "merge_out"),
        str(demo / "raw_json"),
        str(demo / "error_json_2020_08.txt"),
    )




