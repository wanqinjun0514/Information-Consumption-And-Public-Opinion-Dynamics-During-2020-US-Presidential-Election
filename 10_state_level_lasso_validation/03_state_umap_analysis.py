"""Project workflow helper."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import umap
from sklearn.preprocessing import StandardScaler

_rp = Path(__file__).resolve()
for _ in range(8):
    if (_rp / "repo_paths.py").exists():
        if str(_rp) not in sys.path:
            sys.path.insert(0, str(_rp))
        break
    _rp = _rp.parent
else:
    raise RuntimeError("Repository root not found.")

import repo_paths as rp

EPS = 1e-6


def run_state_umap() -> Path:
    csv_path = rp.resolve_df_combined_csv()
    if not csv_path.is_file():
        raise FileNotFoundError(f": {csv_path}")

    plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    df = pd.read_csv(csv_path)
    try:
        df["Y"] = df["Republican Vote Percentage"] - df["Democratic Vote Percentage"]
    except KeyError:
        df["Y"] = df.iloc[:, 3] - df.iloc[:, 2]

    feature_cols = [c for c in df.columns[4:] if "Unnamed" not in c and c != "Y"]
    X_raw = df[feature_cols].select_dtypes(include=[np.number])

    X_safe = X_raw + EPS
    geom_mean = np.exp(np.log(X_safe).mean(axis=1))
    X_clr = np.log(X_safe.div(geom_mean, axis=0))
    X_scaled = StandardScaler().fit_transform(X_clr)

    y_train = df["Y"].values
    reducer = umap.UMAP(
        n_neighbors=25,
        min_dist=0.15,
        n_components=2,
        metric="euclidean",
        target_metric="l2",
        target_weight=0.7,
        random_state=42,
    )
    embedding = reducer.fit_transform(X_scaled, y=y_train)

    umap_df = pd.DataFrame(embedding, columns=["UMAP1", "UMAP2"])
    umap_df["State"] = df["State"]
    umap_df["Y"] = df["Y"]

    plt.figure(figsize=(14, 9))
    sc = plt.scatter(
        umap_df["UMAP1"],
        umap_df["UMAP2"],
        c=umap_df["Y"],
        cmap="coolwarm",
        s=130,
        alpha=0.85,
        edgecolor="k",
        linewidth=0.5,
        vmin=-30,
        vmax=30,
    )
    plt.colorbar(sc, label=" (Rep - Dem)")

    to_label = pd.concat(
        [
            umap_df.nlargest(5, "Y"),
            umap_df.nsmallest(5, "Y"),
            umap_df[umap_df["Y"].abs() < 5],
        ]
    ).drop_duplicates(subset=["State"])
    for _, row in to_label.iterrows():
        plt.annotate(
            row["State"],
            (row["UMAP1"], row["UMAP2"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=10,
            fontweight="bold",
        )

    plt.title("CLR +  UMAP eachstate_abbrevmediaconsumption", fontsize=16)
    plt.grid(True, alpha=0.2)
    out_path = rp.STATE_UMAP_PNG
    rp.ensure_dir(out_path.parent)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[done] {out_path}")
    return out_path


if __name__ == "__main__":
    run_state_umap()
