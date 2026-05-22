"""Project workflow helper."""
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
from media_rating_utils import MEDIA_DATA_PARTS, add_average_bias_points


def process_all_monthly_scores() -> int:
    updated = 0
    for part in MEDIA_DATA_PARTS:
        rating_dir = rp.media_rating_part_dir(part)
        if not rating_dir.is_dir():
            print(f"[skip] directory: {rating_dir}")
            continue
        for csv_path in sorted(rating_dir.glob("user_bias_scores_*.csv")):
            df = pd.read_csv(csv_path)
            df = add_average_bias_points(df)
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            updated += 1
            print(f"[done] {csv_path}")
    return updated


if __name__ == "__main__":
    n = process_all_monthly_scores()
    print(f"\n {n} monthlyfile ")
