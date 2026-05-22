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
from sankey_paths import MONTHS

BIAS_ORDER = [
    "extreme bias left",
    "left",
    "left leaning",
    "center",
    "right leaning",
    "right",
    "extreme bias right",
]

FAKE_NEWS = {"fake news", "fakenews", "fake news "}

USER_BIAS_BINS = [-3 - 1e-9, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3 + 1e-9]


def normalize_part(part: str) -> str:
    return part if part.endswith("_url") else f"{part}_url"


def month_from_output_bias_filename(filename: str) -> str | None:
    """output_with_bias_2019_12.csv   2019_12"""
    if not filename.startswith("output_with_bias_") or not filename.endswith(".csv"):
        return None
    return filename[len("output_with_bias_") : -4]


def state_from_partitioned_filename(state_file: str, source_basename: str) -> str:
    """California_output_with_bias_2019_12.csv   California"""
    suffix = f"_{source_basename}"
    if state_file.endswith(suffix):
        return state_file[: -len(suffix)]
    return state_file.split("_")[0]


def build_id_to_state(state_dir: Path | None = None) -> dict[str, str]:
    """Project workflow helper."""
    state_dir = state_dir or rp.GEO_STATE_INPUT_DIR
    mapping: dict[str, str] = {}
    duplicates = 0
    for path in sorted(state_dir.glob("*.csv")):
        state_name = path.stem
        df = pd.read_csv(path, usecols=["retweeted_user_id"], dtype={"retweeted_user_id": str})
        for uid in df["retweeted_user_id"].dropna().astype(str):
            if uid in mapping and mapping[uid] != state_name:
                duplicates += 1
            mapping[uid] = state_name
    if duplicates:
        print(f"[warning] {duplicates}  user_id state_abbrev state_abbrev ")
    print(f"[information]  {len(mapping):,}  user_id   state_abbrev  {len(list(state_dir.glob('*.csv')))} state_abbrevfile ")
    return mapping


def load_monthly_user_bias_dict(part: str, month: str) -> dict[str, str]:
    """Project workflow helper."""
    path = rp.media_monthly_user_bias_csv(normalize_part(part), month)
    if not path.is_file():
        return {}
    score_df = pd.read_csv(path, dtype={"user_id": str})
    if "average_bias_points" not in score_df.columns:
        raise ValueError(f"{path} missing average_bias_points column")
    score_df["user_bias"] = pd.cut(
        pd.to_numeric(score_df["average_bias_points"], errors="coerce"),
        bins=USER_BIAS_BINS,
        labels=BIAS_ORDER,
        right=False,
    )
    return dict(zip(score_df["user_id"], score_df["user_bias"].astype(str)))


def normalize_bias_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower()


def filter_fake_news_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ("user_bias", "bias"):
        if col in out.columns:
            out[col] = normalize_bias_series(out[col])
            out = out[~out[col].isin(FAKE_NEWS)]
            out = out[out[col].notna() & (out[col] != "nan")]
    return out


def build_bias_crosstab(df: pd.DataFrame) -> pd.DataFrame:
    """Project workflow helper."""
    df = filter_fake_news_df(df)
    if df.empty or "user_bias" not in df.columns or "bias" not in df.columns:
        return pd.DataFrame(0, index=BIAS_ORDER, columns=BIAS_ORDER)
    counts = pd.crosstab(df["user_bias"], df["bias"], dropna=False)
    return counts.reindex(index=BIAS_ORDER, columns=BIAS_ORDER, fill_value=0)


def read_bias_counts_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0)
    df.index = df.index.astype(str).str.strip().str.lower()
    df.columns = df.columns.astype(str).str.strip().str.lower()
    return df.reindex(index=BIAS_ORDER, columns=BIAS_ORDER, fill_value=0)
