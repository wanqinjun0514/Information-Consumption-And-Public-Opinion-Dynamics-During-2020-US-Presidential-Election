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

from media_coexposure_utils import matching_monthly_filename, normalize_domain

MONTHS = [
    "2019_12", "2020_01", "2020_02", "2020_03", "2020_04", "2020_05",
    "2020_06", "2020_07", "2020_08", "2020_09", "2020_10", "2020_11",
    "2020_12", "2021_01", "2021_02",
]

OUTPUT_COLUMNS = [
    "retweet_id",
    "retweeted_user_id",
    "Domain",
    "bias",
    "retweet_origin_user_id",
    "quoted_origin_user_id",
]


def build_domain_bias_lookup() -> dict[str, str]:
    """Project workflow helper."""
    df = pd.read_csv(rp.MEDIA_BIAS_URL_CSV, dtype=str)
    if "domain" not in df.columns or "bias" not in df.columns:
        raise ValueError(f"media URL bias domain,bias: {rp.MEDIA_BIAS_URL_CSV}")
    lookup: dict[str, str] = {}
    for domain, bias in zip(df["domain"], df["bias"]):
        d = normalize_domain(str(domain)) if domain else None
        if d and pd.notna(bias):
            lookup[d] = str(bias).strip()
    print(f"[Step1] media {len(lookup)}  <- {rp.MEDIA_BIAS_URL_CSV}")
    return lookup


def _pick_url(row: pd.Series) -> str | None:
    for col in ("retweet_expanded_urls_array", "quoted_expanded_urls_array"):
        v = row.get(col)
        if v is not None and str(v).strip() and str(v).lower() != "nan":
            return str(v).strip()
    return None


def process_month(month: str, domain_bias: dict[str, str], out_dir: Path) -> Path | None:
    folder = rp.THREE_PARTS_OUTPUT / "external_url" / f"output_{month}"
    if not folder.is_dir():
        print(f"[skip] directory: {folder}")
        return None
    files = sorted(folder.glob("*-output.csv"))
    if not files:
        print(f"[skip]  CSV: {folder}")
        return None

    rows: list[dict] = []
    usecols = [
        "retweet_id",
        "retweeted_user_id",
        "retweet_expanded_urls_array",
        "quoted_expanded_urls_array",
        "retweet_origin_user_id",
        "quoted_origin_user_id",
    ]

    for fpath in files:
        df = pd.read_csv(fpath, dtype=str)
        missing = set(usecols) - set(df.columns)
        if missing:
            print(f"[warning] {fpath.name} column {missing} skipfile")
            continue
        df = df[usecols]
        for _, row in df.iterrows():
            url = _pick_url(row)
            domain = normalize_domain(url)
            if not domain or domain not in domain_bias:
                continue
            rows.append(
                {
                    "retweet_id": row.get("retweet_id", ""),
                    "retweeted_user_id": row["retweeted_user_id"],
                    "Domain": domain,
                    "bias": domain_bias[domain],
                    "retweet_origin_user_id": row.get("retweet_origin_user_id", ""),
                    "quoted_origin_user_id": row.get("quoted_origin_user_id", ""),
                }
            )

    if not rows:
        print(f"[skip] {month} media")
        return None

    out = out_dir / matching_monthly_filename(month)
    pd.DataFrame(rows, columns=OUTPUT_COLUMNS).to_csv(out, index=False)
    print(f"[Step1] {month} -> {out} ({len(rows)} row)")
    return out


def merge_all_months(months: list[str] | None, out_dir: Path) -> Path:
    months = months or MONTHS
    frames = []
    for month in months:
        p = out_dir / matching_monthly_filename(month)
        if p.is_file():
            frames.append(pd.read_csv(p, dtype=str))
    if not frames:
        raise FileNotFoundError(f"monthly matching file: {out_dir}")
    all_df = pd.concat(frames, ignore_index=True).drop_duplicates().reset_index(drop=True)
    out = rp.DIR_03_MEDIA_DOMAIN_BIAS_ALL
    all_df.to_csv(out, index=False)
    print(f"[Step1]  all_data -> {out} ({len(all_df)} row)")
    return out


def run_step1(
    months: list[str] | None = None,
    merge_all: bool = True,
    output_dir: Path | None = None,
) -> None:
    out_dir = rp.ensure_dir(output_dir or rp.DIR_03_MEDIA_RETWEET_DOMAIN_BIAS)
    domain_bias = build_domain_bias_lookup()
    for month in months or MONTHS:
        process_month(month, domain_bias, out_dir)
    if merge_all:
        merge_all_months(months, out_dir)


if __name__ == "__main__":
    run_step1()
