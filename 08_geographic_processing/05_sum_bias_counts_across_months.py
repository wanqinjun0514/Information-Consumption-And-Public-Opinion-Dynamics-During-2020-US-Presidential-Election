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
from geo_utils import BIAS_ORDER, MONTHS, read_bias_counts_csv


def sum_bias_counts_across_months() -> int:
    input_root = rp.GEO_COMBINED_BIAS_COUNTS_DIR
    output_root = rp.GEO_SUM_BIAS_COUNTS_DIR
    rp.ensure_dir(output_root)

    if not input_root.is_dir():
        print(f"[error] row Step04: {input_root}")
        return 0

    state_files: set[str] = set()
    for month in MONTHS:
        month_dir = input_root / month
        if month_dir.is_dir():
            state_files.update(p.name for p in month_dir.glob("*_bias_counts.csv"))

    n_saved = 0
    for csv_name in sorted(state_files):
        dfs = []
        for month in MONTHS:
            path = input_root / month / csv_name
            if path.is_file():
                dfs.append(read_bias_counts_csv(path))

        if not dfs:
            continue

        total = pd.concat(dfs, axis=0).groupby(level=0).sum()
        total = total.reindex(index=BIAS_ORDER, columns=BIAS_ORDER, fill_value=0)
        total.to_csv(output_root / csv_name, encoding="utf-8-sig")
        n_saved += 1

    print(f"[done] Step05 month   {output_root} {n_saved} state_abbrev ")
    return n_saved


def main() -> None:
    sum_bias_counts_across_months()


if __name__ == "__main__":
    main()
