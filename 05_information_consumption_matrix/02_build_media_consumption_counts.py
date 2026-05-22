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

_sankey_dir = rp.DIR_02 / "04_monthly_crosstabs_sankey"
if str(_sankey_dir) not in sys.path:
    sys.path.insert(0, str(_sankey_dir))
from sankey_paths import MONTHS, read_media_monthly_user_bias  # noqa: E402

BIAS_ORDER = [
    "extreme bias left",
    "left",
    "left leaning",
    "center",
    "right leaning",
    "right",
    "extreme bias right",
]

FAKE_NEWS = {"fake news", "fakenews"}

CHANNELS = (
    {
        "part": "external_url",
        "simp_dir": rp.SIMPLIFIED_FORWARDING_MEDIA_EXTERNAL,
        "out_dir": rp.MEDIA_EXTERNAL_INFORMATION_CONSUME,
        "label_csv": rp.MEDIA_BIAS_URL_CSV,
        "key_col": "domain",
        "lookup_col": "matched_domain",
        "normalize_key": lambda x: str(x).strip().lower(),
    },
    {
        "part": "twitter_url",
        "simp_dir": rp.SIMPLIFIED_FORWARDING_MEDIA_TWITTER,
        "out_dir": rp.MEDIA_TWITTER_INFORMATION_CONSUME,
        "label_csv": rp.MEDIA_BIAS_USERNAME_CSV,
        "key_col": "username",
        "lookup_col": "matched_domain",
        "normalize_key": lambda x: str(x).strip(),
    },
    {
        "part": "without_url",
        "simp_dir": rp.SIMPLIFIED_FORWARDING_MEDIA_WITHOUT,
        "out_dir": rp.MEDIA_WITHOUT_INFORMATION_CONSUME,
        "label_csv": rp.MEDIA_BIAS_USERNAME_CSV,
        "key_col": "id_str",
        "lookup_col": "matched_domain",
        "normalize_key": lambda x: str(x).strip(),
    },
)


def _normalize_bias_label(value) -> str | None:
    if pd.isna(value):
        return None
    s = str(value).strip().lower()
    if s in FAKE_NEWS:
        return None
    mapping = {
        "extreme bias left": "extreme bias left",
        "extreme left": "extreme bias left",
        "left": "left",
        "left leaning": "left leaning",
        "center": "center",
        "right leaning": "right leaning",
        "right": "right",
        "extreme bias right": "extreme bias right",
        "extreme right": "extreme bias right",
    }
    return mapping.get(s)


def _build_media_bias_lookup(label_csv: Path, key_col: str, normalize_key) -> dict:
    df = pd.read_csv(label_csv, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    key_col = key_col.lower()
    if key_col not in df.columns or "bias" not in df.columns:
        raise ValueError(f"{label_csv} column {key_col!r}  bias")
    lookup = {}
    for _, row in df.dropna(subset=["bias"]).iterrows():
        key = normalize_key(row[key_col])
        bias = _normalize_bias_label(row["bias"])
        if key and bias:
            lookup[key] = bias
    return lookup


def _scores_to_user_bias(scores_df: pd.DataFrame) -> pd.Series:
    bins = [-3 - 1e-9, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3 + 1e-9]
    return pd.cut(
        scores_df["average_bias_points"],
        bins=bins,
        labels=BIAS_ORDER,
        right=False,
    )


def _months_with_simplified_csv(simp_dir: Path) -> list[str]:
    found = []
    for p in sorted(simp_dir.glob("output_*.csv")):
        month = p.stem.replace("output_", "", 1)
        if month in MONTHS:
            found.append(month)
    return found


def build_consumption_counts_for_channel(channel: dict) -> int:
    part = channel["part"]
    simp_dir: Path = channel["simp_dir"]
    out_dir: Path = channel["out_dir"]
    rp.ensure_dir(out_dir)

    media_lookup = _build_media_bias_lookup(
        channel["label_csv"], channel["key_col"], channel["normalize_key"]
    )
    months = _months_with_simplified_csv(simp_dir)
    if not months:
        print(f"[{part}]  CSV skip: {simp_dir}")
        return 0

    written = 0
    for month in months:
        simp_path = simp_dir / f"output_{month}.csv"
        bias_scores_path = rp.media_monthly_user_bias_csv(part, month)

        if not bias_scores_path.exists():
            print(f"[{part}] skip {month} missinguser {bias_scores_path}")
            continue

        df = pd.read_csv(simp_path, dtype=str)
        lookup_col = channel["lookup_col"]
        df["bias"] = df[lookup_col].map(
            lambda x: media_lookup.get(channel["normalize_key"](x)) if pd.notna(x) else None
        )

        scores = read_media_monthly_user_bias(bias_scores_path)
        scores["user_bias"] = _scores_to_user_bias(scores)
        user_map = dict(zip(scores["user_id"].astype(str), scores["user_bias"].astype(str)))

        df["user_bias"] = df["retweeted_user_id"].astype(str).map(user_map)
        df = df.dropna(subset=["user_bias", "bias"])
        df["user_bias"] = df["user_bias"].map(_normalize_bias_label)
        df["bias"] = df["bias"].map(_normalize_bias_label)
        df = df.dropna(subset=["user_bias", "bias"])

        if df.empty:
            print(f"[{part}] {month} mergerow  0 ")
            matrix = pd.DataFrame(0, index=BIAS_ORDER, columns=BIAS_ORDER)
        else:
            matrix = pd.crosstab(df["user_bias"], df["bias"])
            matrix = matrix.reindex(index=BIAS_ORDER, columns=BIAS_ORDER, fill_value=0)

        out_path = out_dir / f"consumption_counts_{month}.txt"
        matrix.to_csv(out_path, sep="\t")
        print(f"[{part}] {month}   {out_path} row {len(df)}  {int(matrix.values.sum())} ")
        written += 1

    return written


def build_all_media_consumption_counts() -> None:
    total = 0
    for ch in CHANNELS:
        total += build_consumption_counts_for_channel(ch)
    if total == 0:
        print(
            "\ngenerate consumption_counts file  \n"
            "  1) row 01_forwarding_simplify_media_20240904.py\n"
            "  2) row 02 /01 media  media_bias / twitter / without \n"
            "  3)  outputs/media_average_rating/*-rating/user_bias_scores_*.csv"
        )
    else:
        print(f"\n {total} monthlyfile row 02_4a...py plot ")


if __name__ == "__main__":
    build_all_media_consumption_counts()
