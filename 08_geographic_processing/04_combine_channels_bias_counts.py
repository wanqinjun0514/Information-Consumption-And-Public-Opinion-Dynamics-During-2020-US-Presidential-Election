"""Project workflow helper."""
from __future__ import annotations

import argparse
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


def combine_channels_bias_counts() -> int:
    output_root = rp.GEO_COMBINED_BIAS_COUNTS_DIR
    rp.ensure_dir(output_root)

    channel_dirs = [rp.geo_bias_counts_dir(p) for p in rp.GEO_MEDIA_PARTS]
    n_files = 0

    for month in MONTHS:
        template_names: set[str] = set()
        for ch_dir in channel_dirs:
            month_dir = ch_dir / month
            if month_dir.is_dir():
                template_names.update(p.name for p in month_dir.glob("*_bias_counts.csv"))

        if not template_names:
            continue

        month_out = output_root / month
        rp.ensure_dir(month_out)

        for csv_name in sorted(template_names):
            dfs = []
            for ch_dir in channel_dirs:
                path = ch_dir / month / csv_name
                if path.is_file():
                    dfs.append(read_bias_counts_csv(path))

            if not dfs:
                continue

            combined = pd.concat(dfs, axis=0).groupby(level=0).sum()
            combined = combined.reindex(index=BIAS_ORDER, columns=BIAS_ORDER, fill_value=0)
            combined.to_csv(month_out / csv_name, encoding="utf-8-sig")
            n_files += 1

        n_month = len(list(month_out.glob("*.csv")))
        if n_month:
            print(f"[merge] {month}: {n_month} state_abbrevfile")

    print(f"[done] Step04 merge   {output_root} {n_files} file ")
    return n_files


def main() -> None:
    combine_channels_bias_counts()


if __name__ == "__main__":
    main()
