"""Project workflow helper."""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

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

FAKE_NEWS = {"fake news", "fakenews"}

CHANNELS = (
    {
        "part": "external_url",
        "simp_dir": rp.SIMPLIFIED_FORWARDING_MEDIA_EXTERNAL,
        "label_csv": rp.MEDIA_BIAS_URL_CSV,
        "key_col": "domain",
        "lookup_col": "matched_domain",
        "normalize_key": lambda x: str(x).strip().lower(),
        "label_key_normalize": lambda x: extract_domain_external(x),
    },
    {
        "part": "twitter_url",
        "simp_dir": rp.SIMPLIFIED_FORWARDING_MEDIA_TWITTER,
        "label_csv": rp.MEDIA_BIAS_USERNAME_CSV,
        "key_col": "username",
        "lookup_col": "matched_domain",
        "normalize_key": lambda x: str(x).strip(),
        "label_key_normalize": lambda x: str(x).strip(),
    },
    {
        "part": "without_url",
        "simp_dir": rp.SIMPLIFIED_FORWARDING_MEDIA_WITHOUT,
        "label_csv": rp.MEDIA_BIAS_USERNAME_CSV,
        "key_col": "id_str",
        "lookup_col": "matched_domain",
        "normalize_key": lambda x: str(x).strip(),
        "label_key_normalize": lambda x: str(x).strip(),
    },
)


def extract_domain_external(url):
    if pd.isna(url):
        return None
    url_str = str(url).strip("[]'\" ")
    if "," in url_str:
        url_str = url_str.split(",")[0].strip(" '\"")
    if not url_str.startswith(("http://", "https://")):
        url_str = "http://" + url_str
    try:
        parsed = urlparse(url_str)
        domain = parsed.netloc
        if ":" in domain:
            domain = domain.split(":")[0]
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.lower().strip()
    except Exception:
        return None


def _normalize_media_bias(value) -> str | None:
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


def _build_media_bias_lookup(label_csv: Path, key_col: str, key_normalize) -> dict:
    df = pd.read_csv(label_csv, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    key_col = key_col.lower()
    lookup = {}
    for _, row in df.dropna(subset=["bias"]).iterrows():
        raw_key = row.get(key_col)
        if pd.isna(raw_key):
            continue
        key = key_normalize(raw_key)
        bias = _normalize_media_bias(row["bias"])
        if key and bias:
            lookup[key] = bias
    return lookup


def _months_from_simplified(simp_dir: Path) -> list[str]:
    found = []
    for p in sorted(simp_dir.glob("output_*.csv")):
        month = p.stem.replace("output_", "", 1)
        if month in MONTHS:
            found.append(month)
    return found


def build_output_with_bias_for_channel(channel: dict) -> int:
    part = channel["part"]
    simp_dir: Path = channel["simp_dir"]
    media_lookup = _build_media_bias_lookup(
        channel["label_csv"], channel["key_col"], channel["label_key_normalize"]
    )
    months = _months_from_simplified(simp_dir)
    if not months:
        print(f"[{part}] file: {simp_dir}")
        return 0

    written = 0
    for month in months:
        simp_path = simp_dir / f"output_{month}.csv"
        scores_path = rp.media_monthly_user_bias_csv(part, month)
        if not scores_path.exists():
            print(f"[{part}] skip {month}  {scores_path}")
            continue

        df = pd.read_csv(simp_path, dtype=str)
        lookup_col = channel["lookup_col"]
        norm = channel["normalize_key"]
        df["bias"] = df[lookup_col].map(
            lambda x: media_lookup.get(norm(x)) if pd.notna(x) else None
        )

        scores = read_media_monthly_user_bias(scores_path)
        user_map = dict(
            zip(scores["user_id"].astype(str), scores["average_bias_points"].astype(float))
        )
        df["user_average_bias_points"] = df["retweeted_user_id"].astype(str).map(user_map)

        out_path = rp.output_with_bias_monthly_csv(part, month)
        rp.ensure_dir(out_path.parent)
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        valid = df["bias"].notna().sum()
        print(f"[{part}] {month}   {out_path} {len(df)} row media bias {valid} row ")
        written += 1
    return written


def build_all_output_with_bias() -> None:
    total = sum(build_output_with_bias_for_channel(ch) for ch in CHANNELS)
    if total == 0:
        print(
            "\ngeneratefile  \n"
            "  1) 05/01_forwarding_simplify_media row\n"
            "  2) 02/01 media row average_bias_points\n"
        )
    else:
        print(f"\n {total}  output_with_bias file   {rp.OUTPUT_WITH_BIAS_MEDIA_ROOT}")


if __name__ == "__main__":
    build_all_output_with_bias()
