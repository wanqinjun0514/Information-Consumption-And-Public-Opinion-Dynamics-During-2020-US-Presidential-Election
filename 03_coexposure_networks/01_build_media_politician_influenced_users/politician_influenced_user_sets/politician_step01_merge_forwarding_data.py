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

MONTHS = [
    "2019_12", "2020_01", "2020_02", "2020_03", "2020_04", "2020_05",
    "2020_06", "2020_07", "2020_08", "2020_09", "2020_10", "2020_11",
    "2020_12", "2021_01", "2021_02",
]

POLITICIAN_BIASES = frozenset({"Left", "Center", "Right"})


def ensure_politician_bias_lookup() -> Path:
    """Project workflow helper."""
    rp.ensure_dir(rp.DIR_03_COEXPOSURE_INTERMEDIATE)
    out = rp.POLITICIAN_COEXPOSURE_BIAS_CSV
    if out.is_file():
        return out
    src = rp.POLITICIAN_USERNAME_CSV
    if not src.is_file():
        raise FileNotFoundError(f"missingpolitician: {src}")
    df = pd.read_csv(src, dtype=str)
    needed = {"retweet_origin_user_id", "retweet_origin_username", "bias"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"{src} missingcolumn: {missing}")
    df[list(needed)].drop_duplicates().to_csv(out, index=False)
    print(f"[Step1] generate -> {out}")
    return out


def _read_part_month_csvs(part: str, month: str) -> pd.DataFrame | None:
    folder = rp.THREE_PARTS_OUTPUT / part / f"output_{month}"
    if not folder.is_dir():
        print(f"[skip] directory: {folder}")
        return None
    files = sorted(folder.glob("*-output.csv"))
    if not files:
        print(f"[skip]  CSV: {folder}")
        return None
    parts = [pd.read_csv(f, dtype=str) for f in files]
    return pd.concat(parts, ignore_index=True)


def month_data_extraction(month: str, bias_table: pd.DataFrame) -> Path | None:
    """Project workflow helper."""
    bias_cols = bias_table[["retweet_origin_user_id", "retweet_origin_username", "bias"]]

    chunks: list[pd.DataFrame] = []

    ext = _read_part_month_csvs("external_url", month)
    if ext is not None and {"retweeted_user_id", "retweet_origin_username"}.issubset(ext.columns):
        ext = ext[["retweeted_user_id", "retweet_origin_username"]]
        ext = pd.merge(ext, bias_cols, left_on="retweet_origin_username", right_on="retweet_origin_username", how="left")
        chunks.append(ext[["retweeted_user_id", "retweet_origin_user_id", "bias"]])

    tw = _read_part_month_csvs("twitter_url", month)
    if tw is not None and {"retweeted_user_id", "retweet_origin_username"}.issubset(tw.columns):
        tw = tw[["retweeted_user_id", "retweet_origin_username"]]
        tw = pd.merge(tw, bias_cols, left_on="retweet_origin_username", right_on="retweet_origin_username", how="left")
        chunks.append(tw[["retweeted_user_id", "retweet_origin_user_id", "bias"]])

    wo = _read_part_month_csvs("without_url", month)
    if wo is not None and {"retweeted_user_id", "retweet_origin_user_id"}.issubset(wo.columns):
        wo = wo[["retweeted_user_id", "retweet_origin_user_id"]]
        wo = pd.merge(wo, bias_cols, on="retweet_origin_user_id", how="left")
        chunks.append(wo[["retweeted_user_id", "retweet_origin_user_id", "bias"]])

    if not chunks:
        return None

    combined = pd.concat(chunks, ignore_index=True)
    combined = combined.drop_duplicates().reset_index(drop=True)
    filtered = combined.dropna(subset=["retweet_origin_user_id", "bias"])
    filtered = filtered[filtered["bias"].isin(POLITICIAN_BIASES)]

    out_dir = rp.ensure_dir(rp.DIR_03_ALL_TYPES_FILTERED)
    outfile = out_dir / f"output_{month}.csv"
    filtered.to_csv(outfile, index=False)
    print(f"[Step1] {month} -> {outfile} ({len(filtered)} row)")
    return outfile


def merge_all_months_to_all_data(months: list[str] | None = None) -> Path:
    """Project workflow helper."""
    months = months or MONTHS
    out_dir = rp.DIR_03_ALL_TYPES_FILTERED
    frames: list[pd.DataFrame] = []
    for month in months:
        path = out_dir / f"output_{month}.csv"
        if path.is_file():
            frames.append(pd.read_csv(path, dtype=str))
    if not frames:
        raise FileNotFoundError(
            f"monthlyfile: {out_dir}/output_YYYY_MM.csv row month_data_extraction"
        )
    all_data = pd.concat(frames, ignore_index=True).drop_duplicates().reset_index(drop=True)
    out = out_dir / "all_data.csv"
    all_data.to_csv(out, index=False)
    print(f"[Step1]  -> {out} ({len(all_data)} row)")
    return out


def run_step1(months: list[str] | None = None, merge_all: bool = True) -> None:
    bias_table = pd.read_csv(ensure_politician_bias_lookup(), dtype=str)
    for month in months or MONTHS:
        month_data_extraction(month, bias_table)
    if merge_all:
        merge_all_months_to_all_data(months)


if __name__ == "__main__":
    run_step1()
