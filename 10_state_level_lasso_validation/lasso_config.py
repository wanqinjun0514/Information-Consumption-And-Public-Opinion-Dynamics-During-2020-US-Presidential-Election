"""Project workflow helper."""
from __future__ import annotations

import os
import sys
from pathlib import Path

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

PARAM: dict = {}
OUTPUT_DIR: str = ""


def _default_param(*, quick: bool = False) -> dict:
    return {
        "n_outer_iter": 200 if quick else 10000,
        "n_null_iter": 2000 if quick else 100000,
        "lasso_alpha": 0.1,
        "cooks_threshold": 40,
        "freq_threshold": 0.5,
        "p_value_threshold": 0.2,
        "top_n_show": 15,
        "n_keep_states": 40,
        "prop_threshold": 0.0001,
        "file_path": "",
        "out_path": "",
    }


def init_run(*, quick: bool | None = None) -> tuple[dict, str]:
    """Project workflow helper."""
    global PARAM, OUTPUT_DIR
    if quick is None:
        quick = os.environ.get("LASSO_QUICK", "").strip() in ("1", "true", "yes")
    PARAM = _default_param(quick=quick)
    csv_path = rp.resolve_df_combined_csv()
    PARAM["file_path"] = str(csv_path)
    out = rp.LASSO_BOOTSTRAP_OUTPUT_DIR
    rp.ensure_dir(out)
    rp.ensure_dir(rp.DIR_10_PLOTS)
    PARAM["out_path"] = str(out)
    OUTPUT_DIR = PARAM["out_path"]
    print(f"data: {csv_path}")
    print(f"output: {OUTPUT_DIR}")
    if quick:
        print("[] n_outer_iter=200, n_null_iter=2000  --quick ")
    return PARAM, OUTPUT_DIR


def resolve_data_csv() -> Path:
    return Path(PARAM.get("file_path") or rp.resolve_df_combined_csv())
