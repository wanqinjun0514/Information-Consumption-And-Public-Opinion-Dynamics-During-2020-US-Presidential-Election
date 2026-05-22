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
    build_id_to_state,
    month_from_output_bias_filename,
    normalize_part,
)


def split_forwarding_by_state(part: str, id_to_state: dict[str, str] | None = None) -> int:
    part = normalize_part(part)
    id_to_state = id_to_state or build_id_to_state()
    input_dir = rp.output_with_bias_media_dir(part)
    output_root = rp.geo_by_state_dir(part)
    rp.ensure_dir(output_root)

    if not input_dir.is_dir():
        print(f"[skip] inputdirectory: {input_dir}")
        return 0

    n_files = 0
    for csv_path in sorted(input_dir.glob("output_with_bias_*.csv")):
        month = month_from_output_bias_filename(csv_path.name)
        if not month:
            continue
        month_dir = output_root / month
        rp.ensure_dir(month_dir)

        df = pd.read_csv(csv_path, dtype={"retweeted_user_id": str})
        df["state"] = df["retweeted_user_id"].map(id_to_state)
        matched = df["state"].notna().sum()
        print(f"[{part}] {month}: {len(df):,} row, state_abbrev {matched:,} row")

        for state, state_df in df.groupby("state", dropna=True):
            out_path = month_dir / f"{state}_{csv_path.name}"
            state_df.to_csv(out_path, index=False, encoding="utf-8-sig")
            n_files += 1

    print(f"[done] {part} Step01  {n_files} state_abbrev monthfile   {output_root}")
    return n_files


def main() -> None:
    parser = argparse.ArgumentParser(description="state_abbrev output_with_bias")
    parser.add_argument(
        "--part",
        choices=["external", "twitter", "without", "all"],
        default="all",
        help=" all=",
    )
    args = parser.parse_args()
    id_map = build_id_to_state()
    parts = rp.GEO_MEDIA_PARTS if args.part == "all" else (normalize_part(args.part),)
    for p in parts:
        split_forwarding_by_state(p, id_map)


if __name__ == "__main__":
    main()
