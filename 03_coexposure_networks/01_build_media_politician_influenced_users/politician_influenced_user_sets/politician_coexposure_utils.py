"""Project workflow helper."""
from __future__ import annotations

INFLUENCED_SUFFIX = "_influenced_user_set.csv"
POLITICIAN_BIASES = frozenset({"Left", "Center", "Right"})


def parse_influenced_set_filename(file_name: str) -> tuple[str, str] | None:
    if not file_name.endswith(INFLUENCED_SUFFIX):
        return None
    stem = file_name[: -len(INFLUENCED_SUFFIX)]
    parts = stem.split("_")
    if parts and parts[0] in POLITICIAN_BIASES and len(parts) >= 2:
        return parts[1], parts[0]
    if stem:
        return stem, "Unknown"
    return None
