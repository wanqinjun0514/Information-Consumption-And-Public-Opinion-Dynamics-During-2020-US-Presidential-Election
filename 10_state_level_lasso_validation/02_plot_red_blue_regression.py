"""Project workflow helper."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

_rp = Path(__file__).resolve()
_script_dir = _rp.parent
for _ in range(8):
    if (_rp / "repo_paths.py").exists():
        if str(_rp) not in sys.path:
            sys.path.insert(0, str(_rp))
        break
    _rp = _rp.parent
else:
    raise RuntimeError("Repository root not found.")
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

import repo_paths as rp

EPS = 1e-6
DEM_COL = "Democratic Vote Percentage"
REP_COL = "Republican Vote Percentage"


def plot_red_blue_regression() -> Path:
    excel_path = rp.LASSO_FINAL_MODEL_EXCEL
    csv_path = rp.resolve_df_combined_csv()
    if not excel_path.is_file():
        raise FileNotFoundError(f"row Step 01: {excel_path}")
    if not csv_path.is_file():
        raise FileNotFoundError(f"data: {csv_path}")

    print("--- data ---")
    df_coef = pd.read_excel(excel_path, sheet_name="Coefficients_and_VIF")
    intercept = df_coef.loc[df_coef["Feature"] == "const", "Coefficient"].values[0]
    features_info = df_coef[df_coef["Feature"] != "const"][["Feature", "Coefficient"]]
    final_features = features_info["Feature"].tolist()
    final_coefficients = features_info["Coefficient"].values

    df_raw = pd.read_csv(csv_path)
    df_raw["Color"] = np.where(df_raw[DEM_COL] > df_raw[REP_COL], "#3498db", "#e74c3c")
    df_raw["Party"] = np.where(df_raw[DEM_COL] > df_raw[REP_COL], "Democratic", "Republican")
    df_raw["Y_trans"] = np.arcsinh(df_raw.iloc[:, 3] - df_raw.iloc[:, 2])

    numeric_cols = df_raw.select_dtypes(include=[np.number]).columns
    feature_pool = [
        c
        for c in numeric_cols
        if c in df_raw.columns[4:] and c not in ("Y_trans", "Orig_ID")
    ]
    X_raw_numeric = df_raw[feature_pool].copy() + EPS
    geom_mean_all = np.exp(np.log(X_raw_numeric).mean(axis=1))
    X_all_clr = np.log(X_raw_numeric.div(geom_mean_all, axis=0))

    scaler = StandardScaler()
    X_all_scaled = pd.DataFrame(
        scaler.fit_transform(X_all_clr[final_features]), columns=final_features
    )
    y_pred_trans = X_all_scaled.values @ final_coefficients + intercept
    y_true_trans = df_raw["Y_trans"].values
    y_true_raw = np.sinh(y_true_trans)
    y_pred_raw = np.sinh(y_pred_trans)

    print("--- state_abbrev ---")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

    def draw_enhanced_scatter(ax, true_v, pred_v, title, label_x, label_y, *, is_raw=False):
        dem = df_raw["Party"] == "Democratic"
        rep = df_raw["Party"] == "Republican"
        ax.scatter(
            true_v[dem],
            pred_v[dem],
            color="#3498db",
            alpha=0.6,
            edgecolors="white",
            s=80,
            label="Democratic State",
            zorder=3,
        )
        ax.scatter(
            true_v[rep],
            pred_v[rep],
            color="#e74c3c",
            alpha=0.6,
            edgecolors="white",
            s=80,
            label="Republican State",
            zorder=3,
        )
        if is_raw:
            margin = 0.3
            v_range = true_v.max() - true_v.min()
            ax.set_xlim(true_v.min() - v_range * margin, true_v.max() + v_range * margin)
            ax.set_ylim(true_v.min() - v_range * margin, true_v.max() + v_range * margin)
        else:
            all_vals = np.concatenate([true_v, pred_v])
            p1, p99 = np.percentile(all_vals, [1, 99])
            ax.set_xlim(p1 - 1, p99 + 1)
            ax.set_ylim(p1 - 1, p99 + 1)
        curr_lim = ax.get_xlim()
        ax.plot(
            curr_lim,
            curr_lim,
            color="#2c3e50",
            linestyle="--",
            linewidth=2,
            label="Identity Line ($y=x$)",
            zorder=2,
        )
        ax.set_title(title, fontsize=15, fontweight="bold", pad=15)
        ax.set_xlabel(label_x, fontsize=12)
        ax.set_ylabel(label_y, fontsize=12)
        ax.grid(True, linestyle=":", alpha=0.6, zorder=1)
        ax.legend(frameon=True, shadow=True)
        ax.set_aspect("equal", "box")

    draw_enhanced_scatter(
        ax1,
        y_true_trans,
        y_pred_trans,
        "Transformed Scale (arcsinh)",
        "Actual $Y$ (arcsinh)",
        "Predicted $\\hat{Y}$",
    )
    draw_enhanced_scatter(
        ax2,
        y_true_raw,
        y_pred_raw,
        "Original Physical Scale",
        "Actual $Y$ (Raw Diff)",
        "Predicted $\\hat{Y}$ (Restored)",
        is_raw=True,
    )

    plt.tight_layout(pad=3.0)
    out_path = rp.RED_BLUE_REGRESSION_PNG
    rp.ensure_dir(out_path.parent)
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[done] {out_path}")
    return out_path


if __name__ == "__main__":
    plot_red_blue_regression()
