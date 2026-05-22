"""Project workflow helper."""
from __future__ import annotations

import sys
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

from media_coexposure_utils import INFLUENCED_SUFFIX, normalize_bias_label, safe_media_filename


def _collect_matching_files(source_dir: Path) -> list[Path]:
    monthly = sorted(source_dir.glob("matching_top_*_user_id_*.csv"))
    if monthly:
        return monthly
    if (source_dir / "all_data.csv").is_file():
        return [source_dir / "all_data.csv"]
    return []


def run_step2(
    source_dir: Path | None = None,
    output_dir: Path | None = None,
    write_to_coexposure_tree: bool = True,
) -> int:
    source_dir = Path(source_dir or rp.DIR_03_MEDIA_RETWEET_DOMAIN_BIAS)
    output_dir = rp.ensure_dir(output_dir or rp.DIR_03_MEDIA_INFLUENCED_SETS)

    files = _collect_matching_files(source_dir)
    if not files:
        raise FileNotFoundError(
            f" matching_top_*  all_data.csv row Step1: {source_dir}"
        )

    frames = [pd.read_csv(f, dtype=str) for f in files]
    data = pd.concat(frames, ignore_index=True)
    needed = {"retweeted_user_id", "Domain", "bias"}
    missing = needed - set(data.columns)
    if missing:
        raise ValueError(f"Step1 datamissingcolumn: {missing}")

    data["Domain"] = data["Domain"].astype(str).str.strip().str.lower()
    data = data.dropna(subset=["retweeted_user_id", "Domain"])

    count = 0
    grouped = data.groupby(["Domain", "bias"])["retweeted_user_id"].apply(
        lambda s: set(s.dropna().astype(str))
    )

    for (domain, bias_raw), users in grouped.items():
        if not users:
            continue
        bias_folder = normalize_bias_label(bias_raw)
        domain_key = safe_media_filename(domain)
        flat_name = f"{bias_folder.replace(' ', '_')}_{domain_key}{INFLUENCED_SUFFIX}"
        user_df = pd.DataFrame({"retweeted_user_id": sorted(users)})
        user_df.to_csv(output_dir / flat_name, index=False)
        count += 1

        if write_to_coexposure_tree:
            tree_dir = rp.ensure_dir(rp.MEDIA_COEXPOSURE_DATA / bias_folder)
            user_df.to_csv(tree_dir / f"{domain_key}.csv", index=False, header=False)

        print(f"[Step2] {domain} ({bias_folder}): {len(users)} user")

    print(f"[Step2]  {count} media -> {output_dir}")
    return count


if __name__ == "__main__":
    run_step2()
