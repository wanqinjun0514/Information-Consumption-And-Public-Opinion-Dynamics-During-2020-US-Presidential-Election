"""Run the full geographic information-consumption pipeline."""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

_rp = Path(__file__).resolve()
_script_dir = _rp.parent
for _ in range(8):
    if (_rp / "repo_paths.py").exists():
        if str(_rp) not in sys.path:
            sys.path.insert(0, str(_rp))
        break
    _rp = _rp.parent
else:
    raise RuntimeError("Repository root not found; repo_paths.py is missing.")
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

import repo_paths as rp
from geo_utils import build_id_to_state, normalize_part


def _load_step(script_stem: str):
    path = _script_dir / f"{script_stem}.py"
    spec = importlib.util.spec_from_file_location(script_stem, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def run_geo_pipeline(part: str = "all", skip_combine: bool = False) -> None:
    split_mod = _load_step("01_split_forwarding_by_state")
    add_mod = _load_step("02_add_user_bias_by_state")
    crosstab_mod = _load_step("03_build_state_bias_crosstabs")
    combine_mod = _load_step("04_combine_channels_bias_counts")
    sum_mod = _load_step("05_sum_bias_counts_across_months")

    id_map = build_id_to_state()
    parts = rp.GEO_MEDIA_PARTS if part == "all" else (normalize_part(part),)

    for p in parts:
        print(f"\n=== Geographic pipeline: {p} ===")
        split_mod.split_forwarding_by_state(p, id_map)
        add_mod.add_user_bias_by_state(p)
        crosstab_mod.build_state_bias_crosstabs(p)

    if skip_combine:
        return
    if part != "all":
        print("\nSingle-channel run complete. Run with --part all after all channels are ready.")
        return

    print("\n=== Combining channels ===")
    combine_mod.combine_channels_bias_counts()
    print("\n=== Summing across months ===")
    sum_mod.sum_bias_counts_across_months()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 08 geographic information-consumption pipeline.")
    parser.add_argument("--part", choices=["external", "twitter", "without", "all"], default="all")
    parser.add_argument("--skip-combine", action="store_true", help="Run per-channel steps only.")
    args = parser.parse_args()
    run_geo_pipeline(args.part, skip_combine=args.skip_combine)


if __name__ == "__main__":
    main()
