"""Project workflow helper."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
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

QUARTER_MONTHS = [
    ["2019_12", "2020_01", "2020_02"],
    ["2020_03", "2020_04", "2020_05"],
    ["2020_06", "2020_07", "2020_08"],
    ["2020_09", "2020_10"],
    ["2020_11", "2020_12"],
    ["2021_01", "2021_02"],
]
QUARTERS = ["_".join(m) for m in QUARTER_MONTHS]

USER_BIASES = [
    "extreme_left",
    "left",
    "left_leaning",
    "center",
    "right_leaning",
    "right",
    "extreme_right",
]

MEDIA_BIAS_TO_SCORE = {
    "extreme bias left": -3,
    "left": -2,
    "left leaning": -1,
    "center": 0,
    "right leaning": 1,
    "right": 2,
    "extreme bias right": 3,
    "fake news": 3,
}

CHANNELS = ("external", "twitter", "without")


def _media_part_url(datapart: str) -> str:
    return datapart if datapart.endswith("_url") else f"{datapart}_url"


def calculate_g(p: float, q: float) -> float:
    """Project workflow helper."""
    if (np.sign(p) * np.sign(q) < 0) or (p == 0 and abs(q) > 1):
        return 2 * abs(p - q)
    return abs(p - q)


def calculate_quarterly_media_information_openness_continuous(datapart: str = "external") -> None:
    """Project workflow helper."""
    part_url = _media_part_url(datapart)
    print(f"\n{'=' * 60}\n IdeoP   : {part_url}\n{'=' * 60}")

    for user_bias in USER_BIASES:
        print(f"  political_bias: {user_bias}")
        for quarter, quarter_months in zip(QUARTERS, QUARTER_MONTHS):
            user_file_path = rp.media_quarter_cohort_csv(part_url, quarter, user_bias)
            if not user_file_path.is_file():
                continue

            user_df = pd.read_csv(
                user_file_path,
                usecols=["user_id", "average_bias_points"],
                dtype={"user_id": str},
            )
            user_pu_dict = dict(zip(user_df["user_id"], user_df["average_bias_points"]))
            user_score_sum_dict = {uid: 0.0 for uid in user_pu_dict}
            user_count_dict = {uid: 0 for uid in user_pu_dict}

            for file_path in (rp.output_with_bias_monthly_csv(part_url, m) for m in quarter_months):
                if not file_path.is_file():
                    continue
                df_iter = pd.read_csv(
                    file_path,
                    usecols=["retweeted_user_id", "bias"],
                    dtype=str,
                )
                for row in df_iter.itertuples(index=False):
                    uid = row.retweeted_user_id
                    if uid not in user_pu_dict:
                        continue
                    p_u = user_pu_dict[uid]
                    p_i = MEDIA_BIAS_TO_SCORE.get(str(row.bias).lower(), 0)
                    user_score_sum_dict[uid] += calculate_g(p_u, p_i)
                    user_count_dict[uid] += 1

            final_data = []
            for uid in user_pu_dict:
                count = user_count_dict[uid]
                total_g = user_score_sum_dict[uid]
                ideo_p = total_g / count if count > 0 else 0.0
                final_data.append(
                    {
                        "user_id": uid,
                        "info_score": total_g,
                        "appear_count": count,
                        "average_info_openmindness": ideo_p,
                    }
                )

            result_df = pd.DataFrame(final_data)[
                ["user_id", "info_score", "appear_count", "average_info_openmindness"]
            ]
            output_path = rp.openmindness_continuous_score_csv(part_url, user_bias, quarter)
            rp.ensure_dir(output_path.parent)
            result_df.to_csv(output_path, index=False, encoding="utf-8-sig")
            print(f"    [{quarter}]   {output_path.name} ({len(result_df)} user)")


def merge_three_source_continuous_openmindness() -> None:
    """external + twitter + without   continuous/total/{bias}/ """
    base_dir = rp.OPENMINDNESS_CONTINUOUS
    source_folders = ["external", "twitter", "without"]
    target_dir = rp.OPENMINDNESS_CONTINUOUS_TOTAL

    print(f"\n{'=' * 60}\nmerge   {target_dir}\n{'=' * 60}")

    for bias in USER_BIASES:
        print(f"  political_bias: {bias}")
        bias_target_dir = target_dir / bias
        rp.ensure_dir(bias_target_dir)

        all_filenames: set[str] = set()
        for source in source_folders:
            source_path = base_dir / source / bias
            if source_path.is_dir():
                all_filenames.update(
                    f.name for f in source_path.iterdir() if f.suffix == ".csv"
                )

        if not all_filenames:
            print(f"    [skip]  CSV")
            continue

        for filename in sorted(all_filenames):
            dfs = []
            for source in source_folders:
                file_path = base_dir / source / bias / filename
                if not file_path.is_file():
                    continue
                df = pd.read_csv(file_path)
                if {"info_score", "appear_count"}.issubset(df.columns):
                    dfs.append(df)

            if not dfs:
                continue

            combined_df = pd.concat(dfs, ignore_index=True)
            result_df = (
                combined_df.groupby("user_id")[["info_score", "appear_count"]]
                .sum()
                .reset_index()
            )
            result_df["average_score"] = np.where(
                result_df["appear_count"] > 0,
                result_df["info_score"] / result_df["appear_count"],
                0.0,
            )
            result_df = result_df.rename(
                columns={
                    "info_score": "total_info_score",
                    "appear_count": "total_appear_count",
                }
            )
            result_df = result_df[
                ["user_id", "total_info_score", "total_appear_count", "average_score"]
            ]
            save_path = bias_target_dir / filename
            result_df.to_csv(save_path, index=False, encoding="utf-8-sig")

    print("\nmergedone ")


def run_continuous_openmindness_pipeline() -> None:
    """Project workflow helper."""
    for part in CHANNELS:
        calculate_quarterly_media_information_openness_continuous(part)
    merge_three_source_continuous_openmindness()


if __name__ == "__main__":
    #   05/01_forwarding_simplify_media_20240904.py
    #   06/01_build_output_with_bias_media.py

    run_continuous_openmindness_pipeline()

