"""Project workflow helper."""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import pandas as pd
import plotly.express as px

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
from map_plot_utils import (
    COLOR_RANGE,
    COLOR_SCALE_20260420,
    COLOR_SCALE_LEGACY_PDF,
    MIDPOINT_20260420,
    MIDPOINT_LEGACY_PDF,
    prepare_locations_column,
)

try:
    from tqdm.auto import tqdm
except ImportError:
    tqdm = None


def plot_us_state_choropleth(
    *,
    csv_path: Path | None = None,
    style: str = "20260420",
    fix_locations: bool = False,
    export_html: bool = True,
    export_pdf: bool = False,
    html_name: str = "Figure_US_states_choropleth_20260420.html",
    show: bool = False,
) -> None:
    csv_path = csv_path or rp.STATE_USER_BIAS_PROPORTION_CSV
    if not csv_path.is_file():
        raise FileNotFoundError(f"datafile: {csv_path}")

    if style == "legacy-pdf":
        color_scale = COLOR_SCALE_LEGACY_PDF
        midpoint = MIDPOINT_LEGACY_PDF
    else:
        color_scale = COLOR_SCALE_20260420
        midpoint = MIDPOINT_20260420

    rp.ensure_dir(rp.DIR_09_OUTPUTS)
    t_all = time.perf_counter()
    steps = 2 + int(export_html) + int(export_pdf) + int(show)
    pbar = tqdm(total=steps, desc="4a", unit="") if tqdm else None

    def _tick(label: str) -> None:
        if pbar:
            pbar.update(1)
            pbar.set_postfix_str(label)

    df_scores = pd.read_csv(csv_path, encoding="utf-8-sig")
    df_scores.columns = df_scores.columns.str.strip()
    if fix_locations:
        df_scores = prepare_locations_column(df_scores)
        loc_col = "plot_loc"
    else:
        loc_col = "state_abbrev"
    _tick("CSV")

    fig = px.choropleth(
        df_scores,
        locations=loc_col,
        locationmode="USA-states",
        color="normalized_ratio",
        color_continuous_scale=color_scale,
        color_continuous_midpoint=midpoint,
        range_color=list(COLOR_RANGE),
        labels={"normalized_ratio": "State Score"},
        title="USA States Map with Custom Coloring",
    )
    fig.update_geos(
        projection_type="albers usa",
        visible=False,
        scope="usa",
    )
    _tick(" choropleth")

    if export_html:
        html_path = rp.DIR_09_OUTPUTS / html_name
        fig.write_html(str(html_path), include_plotlyjs="cdn", full_html=True)
        print(f"[done] HTML: {html_path}")
        _tick("write_html")

    if export_pdf:
        import plotly.io as pio

        pdf_path = rp.DIR_09_OUTPUTS / "Figure_US_states_choropleth.pdf"
        pio.write_image(fig, str(pdf_path), format="pdf", width=5000, height=7000)
        print(f"[done] PDF: {pdf_path}")
        _tick("write_image")

    if show:
        fig.show()
        _tick("fig.show")

    if pbar:
        pbar.close()
    print(f"[done] style={style} midpoint={midpoint}  {time.perf_counter() - t_all:.2f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="USeachstate_abbrevmap =20260420  ")
    parser.add_argument("--csv", type=Path, default=None)
    parser.add_argument(
        "--style",
        choices=["20260420", "legacy-pdf"],
        default="20260420",
        help="20260420= HTML  legacy-pdf= PDF  +midpoint0.3 ",
    )
    parser.add_argument("--fix-locations", action="store_true", help=" plot_loc  DC   state_abbrev  ")
    parser.add_argument("--pdf", action="store_true")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--no-html", action="store_true")
    args = parser.parse_args()
    plot_us_state_choropleth(
        csv_path=args.csv,
        style=args.style,
        fix_locations=args.fix_locations,
        export_html=not args.no_html,
        export_pdf=args.pdf,
        show=args.show,
    )


if __name__ == "__main__":
    main()
