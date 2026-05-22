"""Project workflow helper."""
from __future__ import annotations

import sys
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

from politician_coexposure_utils import INFLUENCED_SUFFIX


def run_step2(
    input_file: Path | None = None,
    output_directory: Path | None = None,
) -> int:
    input_file = Path(input_file or rp.DIR_03_ALL_TYPES_FILTERED / "all_data.csv")
    output_directory = Path(output_directory or rp.POLITICIAN_INFLUENCED_SETS)
    rp.ensure_dir(output_directory)

    if not input_file.is_file():
        raise FileNotFoundError(f"missing Step1 output: {input_file}")

    data = pd.read_csv(
        input_file,
        dtype={"retweeted_user_id": "str", "retweet_origin_user_id": "str", "bias": "str"},
    )
    needed = {"retweeted_user_id", "retweet_origin_user_id", "bias"}
    missing = needed - set(data.columns)
    if missing:
        raise ValueError(f"{input_file} missingcolumn: {missing}")

    count = 0
    grouped = data.groupby(["retweet_origin_user_id", "bias"])["retweeted_user_id"].apply(
        lambda s: set(s.dropna().astype(str))
    )
    for (origin_user_id, bias), influenced_users in grouped.items():
        if not influenced_users:
            continue
        out_name = f"{bias}_{origin_user_id}{INFLUENCED_SUFFIX}"
        out_path = output_directory / out_name
        pd.DataFrame({"retweeted_user_id": sorted(influenced_users)}).to_csv(out_path, index=False)
        count += 1
        print(f"[Step2] {len(influenced_users)} user -> {out_path.name}")

    print(f"[Step2] write {count} politicianuser -> {output_directory}")
    return count


if __name__ == "__main__":
    run_step2()
