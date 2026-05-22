# -*- coding: utf-8 -*-
"""Project workflow helper."""

import re
import sys
import os
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

OUT_CSV = rp.PLOT_DATA_ALL_SOURCES_RAW_CSV
CHUNKSIZE = 200_000


def infer_quarter_from_filename(filename: str, bias: str) -> str:
    """Project workflow helper."""
    base = os.path.basename(filename)
    name = os.path.splitext(base)[0]
    token = f"_{bias}"
    if token in name:
        return name.split(token)[0]
    m = re.match(r"^(\d{4}_\d{2}_.+?)_", name)
    return m.group(1) if m else name


def find_openmindness_col(cols) -> str:
    for c in ["average_info_openmindness", "openmindness", "avg_openmindness"]:
        if c in cols:
            return c
    return ""


def main():
    sources = ["external", "twitter", "without", "total"]

    rp.ensure_dir(OUT_CSV.parent)
    if OUT_CSV.exists():
        OUT_CSV.unlink()

    wrote_header = False
    total_written = 0

    for source in sources:
        source_dir = rp.openmindness_source_scan_dir(source)
        if not source_dir.is_dir():
            print(f"[WARN] directory: {source_dir} skip")
            continue

        bias_dirs = [d.name for d in source_dir.iterdir() if d.is_dir()]
        if not bias_dirs:
            print(f"[WARN] {source_dir} biasfile skip")
            continue

        for bias in bias_dirs:
            bias_dir = source_dir / bias
            csv_files = sorted(bias_dir.glob("*.csv"))
            if not csv_files:
                continue

            for fp in csv_files:
                quarter = infer_quarter_from_filename(str(fp), bias=bias)
                print(f"[READ] {source}/{bias} -> {fp.name}")

                if source == "total":
                    # total: user_id,total_info_score,total_appear_count,average_score
                    preferred_cols = ["user_id", "total_info_score", "total_appear_count", "average_score"]
                    try:
                        it = pd.read_csv(fp, usecols=preferred_cols, chunksize=CHUNKSIZE)
                        uid_col = "user_id"
                        info_col = "total_info_score"
                        appear_col = "total_appear_count"
                        om_col = "average_score"
                    except Exception:
                        it = pd.read_csv(fp, chunksize=CHUNKSIZE)
                        uid_col = "user_id"
                        info_col = ""
                        appear_col = ""
                        om_col = ""
                else:
                    # external/twitter/without: user_id,info_score,appear_count,average_info_openmindness
                    preferred_cols = ["user_id", "info_score", "appear_count", "average_info_openmindness"]
                    try:
                        it = pd.read_csv(fp, usecols=preferred_cols, chunksize=CHUNKSIZE)
                        uid_col = "user_id"
                        info_col = "info_score"
                        appear_col = "appear_count"
                        om_col = "average_info_openmindness"
                    except Exception:
                        it = pd.read_csv(fp, chunksize=CHUNKSIZE)
                        uid_col = "user_id"
                        info_col = ""
                        appear_col = ""
                        om_col = ""

                for chunk in it:
                    if uid_col not in chunk.columns:
                        continue

                    if source == "total":
                        if not appear_col:
                            appear_col2 = "total_appear_count" if "total_appear_count" in chunk.columns else ""
                        else:
                            appear_col2 = appear_col

                        if not om_col:
                            om_col2 = "average_score" if "average_score" in chunk.columns else ""
                        else:
                            om_col2 = om_col

                        if not info_col:
                            info_col2 = "total_info_score" if "total_info_score" in chunk.columns else ""
                        else:
                            info_col2 = info_col
                    else:
                        if not appear_col:
                            appear_col2 = "appear_count" if "appear_count" in chunk.columns else ""
                        else:
                            appear_col2 = appear_col

                        if not om_col:
                            om_col2 = find_openmindness_col(chunk.columns)
                        else:
                            om_col2 = om_col

                        if not info_col:
                            info_col2 = "info_score" if "info_score" in chunk.columns else ""
                        else:
                            info_col2 = info_col

                    if not appear_col2 or not om_col2:
                        continue
                    if appear_col2 not in chunk.columns or om_col2 not in chunk.columns:
                        continue

                    out = pd.DataFrame({
                        "source": source,
                        "bias": bias,
                        "quarter": quarter,
                        "user_id": chunk[uid_col].astype(str),
                        "info_score": pd.to_numeric(chunk[info_col2], errors="coerce") if info_col2 and info_col2 in chunk.columns else np.nan,
                        "appear_count": pd.to_numeric(chunk[appear_col2], errors="coerce"),
                        "average_info_openmindness": pd.to_numeric(chunk[om_col2], errors="coerce"),
                    })

                    out.to_csv(
                        OUT_CSV,
                        mode="a",
                        index=False,
                        header=(not wrote_header),
                        encoding="utf-8-sig",
                    )
                    wrote_header = True
                    total_written += len(out)

                print(f"[OK] writerow: {total_written}")

    if not wrote_header:
        raise RuntimeError("data directoryCSVcolumn ")

    print(f"\n[Done] datagenerate: {OUT_CSV}")
    print(f"[Info] row(): {total_written}")


if __name__ == "__main__":
    main()
