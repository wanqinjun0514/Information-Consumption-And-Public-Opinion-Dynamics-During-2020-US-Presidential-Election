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
from geo_utils import MONTHS, load_monthly_user_bias_dict, normalize_part


def add_user_bias_by_state(part: str) -> int:
    part = normalize_part(part)
    input_root = rp.geo_by_state_dir(part)
    output_root = rp.geo_with_user_bias_dir(part)
    rp.ensure_dir(output_root)

    n_files = 0
    for month in MONTHS:
        month_in = input_root / month
        if not month_in.is_dir():
            continue
        user_bias_dict = load_monthly_user_bias_dict(part, month)
        if not user_bias_dict:
            print(f"[skip] {part} {month}:  user_bias_scores")
            continue

        month_out = output_root / month
        rp.ensure_dir(month_out)
        for csv_path in sorted(month_in.glob("*.csv")):
            df = pd.read_csv(csv_path, dtype={"retweeted_user_id": str})
            df["user_bias"] = df["retweeted_user_id"].map(user_bias_dict)
            df.to_csv(month_out / csv_path.name, index=False, encoding="utf-8-sig")
            n_files += 1
        print(f"[{part}] {month}: process {len(list(month_in.glob('*.csv')))} state_abbrevfile")

    print(f"[done] {part} Step02   {output_root} {n_files} file ")
    return n_files


def main() -> None:
    parser = argparse.ArgumentParser(description="state_abbrev user_bias")
    parser.add_argument("--part", choices=["external", "twitter", "without", "all"], default="all")
    args = parser.parse_args()
    parts = rp.GEO_MEDIA_PARTS if args.part == "all" else (normalize_part(args.part),)
    for p in parts:
        add_user_bias_by_state(p)


if __name__ == "__main__":
    main()
