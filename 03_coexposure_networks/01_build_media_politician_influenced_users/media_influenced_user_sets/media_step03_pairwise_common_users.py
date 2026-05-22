"""Project workflow helper."""
from __future__ import annotations

import os
import sys
from itertools import combinations
from pathlib import Path

import pandas as pd

_rp = Path(__file__).resolve()
for _ in range(10):
    if (_rp / "repo_paths.py").exists():
        if str(_rp) not in sys.path:
            sys.path.insert(0, str(_rp))
        break
    _rp = _rp.parent
else:
    raise RuntimeError("Repository root not found; repo_paths.py is missing.")

import repo_paths as rp

from media_coexposure_utils import parse_influenced_set_filename


def run_step3(
    input_dir: Path | None = None,
    output_file: Path | None = None,
    sort_output: bool = True,
    min_common: int = 1,
) -> pd.DataFrame:
    input_dir = Path(input_dir or rp.DIR_03_MEDIA_INFLUENCED_SETS)
    output_file = Path(
        output_file or rp.DIR_03_COEXPOSURE_INTERMEDIATE / "media_common_influenced_users.csv"
    )
    rp.ensure_dir(output_file.parent)

    media_users: dict[str, set[str]] = {}
    media_bias: dict[str, str] = {}

    for file_name in os.listdir(input_dir):
        parsed = parse_influenced_set_filename(file_name)
        if not parsed:
            continue
        media_key, bias = parsed
        path = input_dir / file_name
        try:
            df = pd.read_csv(path, usecols=["retweeted_user_id"], dtype={"retweeted_user_id": "str"})
        except ValueError:
            df = pd.read_csv(path, header=None, dtype=str)
            df.columns = ["retweeted_user_id"]
        users = set(df["retweeted_user_id"].dropna())
        media_users[media_key] = users
        media_bias[media_key] = bias
        print(f"[Step3] {file_name}: {len(users)} user")

    if len(media_users) < 2:
        raise RuntimeError(f"media 2 : {input_dir}")

    results = []
    for m1, m2 in combinations(media_users.keys(), 2):
        n = len(media_users[m1] & media_users[m2])
        if n >= min_common:
            results.append([m1, m2, media_bias.get(m1, ""), media_bias.get(m2, ""), n])

    result_df = pd.DataFrame(
        results,
        columns=["media_1", "media_2", "bias_1", "bias_2", "common_user_count"],
    )
    result_df.to_csv(output_file, index=False)
    print(f"[Step3] {len(result_df)}  -> {output_file}")

    if sort_output:
        sorted_path = rp.MEDIA_PAIRWISE_EDGES_CSV
        result_df.sort_values("common_user_count", ascending=False).to_csv(sorted_path, index=False)
        print(f"[Step3]  -> {sorted_path}")
        return result_df.sort_values("common_user_count", ascending=False)

    return result_df


if __name__ == "__main__":
    run_step3()
