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
from geo_utils import (
    MONTHS,
    build_bias_crosstab,
    normalize_part,
    state_from_partitioned_filename,
)


def build_state_bias_crosstabs(part: str) -> int:
    part = normalize_part(part)
    input_root = rp.geo_with_user_bias_dir(part)
    output_root = rp.geo_bias_counts_dir(part)
    rp.ensure_dir(output_root)

    n_files = 0
    for month in MONTHS:
        month_in = input_root / month
        if not month_in.is_dir():
            continue
        month_out = output_root / month
        rp.ensure_dir(month_out)

        for csv_path in sorted(month_in.glob("*.csv")):
            df = pd.read_csv(csv_path, dtype={"retweeted_user_id": str})
            if "state" in df.columns and df["state"].notna().any():
                state = str(df["state"].dropna().iloc[0])
            elif "_output_with_bias_" in csv_path.name:
                state = csv_path.name.split("_output_with_bias_")[0]
            else:
                state = state_from_partitioned_filename(csv_path.name, csv_path.name)

            counts = build_bias_crosstab(df)
            out_name = f"{state}_bias_counts.csv"
            counts.to_csv(month_out / out_name, encoding="utf-8-sig")
            n_files += 1

        n_month = len(list(month_out.glob("*.csv"))) if month_out.is_dir() else 0
        if n_month:
            print(f"[{part}] {month}: {n_month} state_abbrev 7 7 ")

    print(f"[done] {part} Step03   {output_root} {n_files} file ")
    return n_files


def main() -> None:
    parser = argparse.ArgumentParser(description="generatestate_abbrev month 7 7 crosstab")
    parser.add_argument("--part", choices=["external", "twitter", "without", "all"], default="all")
    args = parser.parse_args()
    parts = rp.GEO_MEDIA_PARTS if args.part == "all" else (normalize_part(args.part),)
    for p in parts:
        build_state_bias_crosstabs(p)


if __name__ == "__main__":
    main()
