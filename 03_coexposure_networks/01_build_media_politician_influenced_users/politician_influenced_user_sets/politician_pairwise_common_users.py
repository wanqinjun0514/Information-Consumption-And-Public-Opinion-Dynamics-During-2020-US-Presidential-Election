"""Project workflow helper."""
from __future__ import annotations

import os
import sys
from itertools import combinations
from pathlib import Path

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

from politician_coexposure_utils import INFLUENCED_SUFFIX, parse_influenced_set_filename


def run_step3(
    input_dir: Path | None = None,
    output_file: Path | None = None,
    sort_output: bool = True,
) -> pd.DataFrame:
    input_dir = Path(input_dir or rp.POLITICIAN_INFLUENCED_SETS)
    output_file = Path(
        output_file or rp.DIR_03_COEXPOSURE_INTERMEDIATE / "politician_common_influenced_users.csv"
    )
    rp.ensure_dir(output_file.parent)

    politician_users: dict[str, set[str]] = {}
    pol_bias: dict[str, str] = {}

    for file_name in os.listdir(input_dir):
        parsed = parse_influenced_set_filename(file_name)
        if not parsed:
            continue
        pol_id, bias = parsed
        path = input_dir / file_name
        users = set(
            pd.read_csv(path, usecols=["retweeted_user_id"], dtype={"retweeted_user_id": "str"})[
                "retweeted_user_id"
            ].dropna()
        )
        politician_users[pol_id] = users
        pol_bias[pol_id] = bias
        print(f"[Step3] read {file_name}: {len(users)} user")

    if len(politician_users) < 2:
        raise RuntimeError(f"politician 2  : {input_dir}")

    results = []
    for pol1, pol2 in combinations(politician_users.keys(), 2):
        common_count = len(politician_users[pol1] & politician_users[pol2])
        if common_count > 0:
            results.append([pol1, pol2, common_count])

    result_df = pd.DataFrame(results, columns=["politician_id_1", "politician_id_2", "common_user_count"])
    result_df.to_csv(output_file, index=False)
    print(f"[Step3] {len(result_df)}  -> {output_file}")

    if sort_output:
        sorted_path = output_file.with_name("politician_common_influenced_users_sorted.csv")
        result_df.sort_values("common_user_count", ascending=False).to_csv(sorted_path, index=False)
        print(f"[Step3]  -> {sorted_path}")
        return result_df.sort_values("common_user_count", ascending=False)

    return result_df


def compute_pairwise_politician_intersections_with_sets():
    return run_step3(sort_output=True)


def sort_common_user_count_descending():
    src = rp.DIR_03_COEXPOSURE_INTERMEDIATE / "politician_common_influenced_users.csv"
    dst = rp.DIR_03_COEXPOSURE_INTERMEDIATE / "politician_common_influenced_users_sorted.csv"
    df = pd.read_csv(src)
    df.sort_values("common_user_count", ascending=False).to_csv(dst, index=False)
    print(f" -> {dst}")


if __name__ == "__main__":
    run_step3()
