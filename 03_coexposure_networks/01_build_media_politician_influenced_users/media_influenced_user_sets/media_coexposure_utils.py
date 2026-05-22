"""Project workflow helper."""
from __future__ import annotations

import re
from urllib.parse import urlparse

import pandas as pd

INFLUENCED_SUFFIX = "_influenced_user_set.csv"
MATCHING_MONTHLY_GLOB = "matching_top_*_user_id_*.csv"

MEDIA_BIAS_FOLDERS = frozenset({
    "Center", "Extreme Bias Left", "Extreme Bias Right", "Fake News",
    "Left", "Left Leaning", "Right", "Right Leaning",
})

BIAS_TO_FOLDER = {
    "center": "Center",
    "left": "Left",
    "right": "Right",
    "left leaning": "Left Leaning",
    "right leaning": "Right Leaning",
    "extreme bias left": "Extreme Bias Left",
    "extreme bias right": "Extreme Bias Right",
    "fake news": "Fake News",
}


def normalize_domain(url: str | None) -> str | None:
    if url is None or (isinstance(url, float) and pd.isna(url)):
        return None
    s = str(url).strip()
    if not s or s.lower() == "nan":
        return None
    if "://" not in s:
        s = "http://" + s
    try:
        host = urlparse(s).netloc.lower()
    except Exception:
        return None
    if host.startswith("www."):
        host = host[4:]
    return host or None


def normalize_bias_label(bias: str) -> str:
    key = str(bias).strip().lower()
    return BIAS_TO_FOLDER.get(key, bias.strip())


def safe_media_filename(domain: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", domain.strip())


def matching_monthly_filename(month: str) -> str:
    """Project workflow helper."""
    return f"matching_top_200_user_id_{month}.csv"


def parse_influenced_set_filename(file_name: str) -> tuple[str, str] | None:
    """Project workflow helper."""
    if not file_name.endswith(INFLUENCED_SUFFIX):
        return None
    stem = file_name[: -len(INFLUENCED_SUFFIX)]
    for folder in sorted(MEDIA_BIAS_FOLDERS, key=len, reverse=True):
        prefix = folder.replace(" ", "_")
        if stem.startswith(prefix + "_"):
            return stem[len(prefix) + 1 :], folder
    parts = stem.split("_", 1)
    if len(parts) == 2 and parts[0] in MEDIA_BIAS_FOLDERS:
        return parts[1], parts[0]
    if stem:
        return stem, "Unknown"
    return None
