"""Project workflow helper."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_REPO = _ROOT
for _ in range(8):
    if (_REPO / "repo_paths.py").exists():
        if str(_REPO) not in sys.path:
            sys.path.insert(0, str(_REPO))
        break
    _REPO = _REPO.parent
else:
    raise RuntimeError("Repository root not found; repo_paths.py is missing.")

import repo_paths as rp


def _run(script: str, extra: list[str] | None = None) -> None:
    cmd = [sys.executable, str(_ROOT / script)] + (extra or [])
    print(f"\n>>> {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=str(_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="10 Lasso ")
    parser.add_argument("--quick", action="store_true", help="Step01  bootstrap ")
    parser.add_argument("--skip-umap", action="store_true", help="skip UMAP")
    parser.add_argument("--only-plot", action="store_true", help=" Step02/03  Step01  ")
    args = parser.parse_args()

    csv_path = rp.resolve_df_combined_csv()
    if not csv_path.is_file():
        raise FileNotFoundError(
            f" df_combined.csv :\n  {rp.DIR_10_INPUTS}\n   {rp.DIR_10}/df_combined.csv"
        )

    extra = ["--quick"] if args.quick else []
    if not args.only_plot:
        _run("01_run_bootstrap_lasso.py", extra)
    _run("02_plot_red_blue_regression.py")
    if not args.skip_umap:
        try:
            import umap  # noqa: F401
        except ImportError:
            print("[skip]  umap-learn Step03 skip row: pip install umap-learn")
        else:
            _run("03_state_umap_analysis.py")
    print("\n[done] 10  ")


if __name__ == "__main__":
    main()
