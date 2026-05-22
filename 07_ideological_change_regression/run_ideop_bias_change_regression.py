# -*- coding: utf-8 -*-
"""Project workflow helper."""

import os
import sys
from pathlib import Path

import glob

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib import rcParams

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


# ======================
# ======================
SOURCES = ["external", "twitter", "without"]

QUARTERS = [
    "2019_12_2020_01_2020_02",
    "2020_03_2020_04_2020_05",
    "2020_06_2020_07_2020_08",
    "2020_09_2020_10",
    "2020_11_2020_12",
    "2021_01_2021_02"
]

POLITICAL_BIAS_FOLDERS = [
    "extreme_left",
    "left",
    "left_leaning",
    "center",
    "right_leaning",
    "right",
    "extreme_right"
]

APPEAR_COUNT_THRESHOLD = 2

MIN_N_PER_GROUP = 2

USE_IQR_OUTLIER_FILTER = True

DEBUG_PRINT_HEAD_ROWS = 5
DEBUG_PRINT_XY_EXAMPLES = True
DEBUG_MAX_GROUP_EXAMPLES = 8


# ======================
# ======================
OUT_DIR = str(rp.DIR_06_REGRESSION_OUTPUT)
os.makedirs(OUT_DIR, exist_ok=True)


# ======================
# ======================
def remove_outliers_iqr(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if df.empty:
        return df
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1
    if pd.isna(IQR) or IQR == 0:
        return df
    lower = Q1 - 1.5 * IQR
    upper = Q3 + 1.5 * IQR
    return df[(df[column] >= lower) & (df[column] <= upper)]


def find_bias_file(source: str, quarter: str) -> str:
    part = source if source.endswith("_url") else f"{source}_url"
    base_dir = rp.media_rating_part_dir(part)
    exact = base_dir / f"quarterly_user_bias_scores_{quarter}.csv"
    if exact.is_file():
        return str(exact)
    cohort = base_dir / "user_bias_scores_by_quarter" / f"quarterly_user_bias_scores_{quarter}.csv"
    if cohort.is_file():
        return str(cohort)
    cand = sorted(base_dir.glob(f"*{quarter}*.csv"))
    return str(cand[0]) if cand else ""


# --------------------------
# --------------------------
def load_bias_quarter_avg(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    if df.empty:
        return df

    id_col = "user_id" if "user_id" in df.columns else df.columns[0]
    bias_col = "average_bias_points" if "average_bias_points" in df.columns else df.columns[-1]

    out = df[[id_col, bias_col]].copy()
    out.columns = ["user_id", "average_bias_points"]
    out["user_id"] = out["user_id"].astype(str)
    out["average_bias_points"] = pd.to_numeric(out["average_bias_points"], errors="coerce")
    out = out.dropna(subset=["average_bias_points"])
    return out


def build_bias_change_for_source(source: str) -> pd.DataFrame:
    quarter_to_df = {}

    for q in QUARTERS:
        fp = find_bias_file(source, q)
        if not fp:
            print(f"[WARN-bias]  {source}  bias quarterfile: {q}")
            continue
        print(f"[READ-bias] {source} quarter={q} -> {os.path.basename(fp)}")
        quarter_to_df[q] = load_bias_quarter_avg(fp)

    pairs = [(QUARTERS[i], QUARTERS[i + 1]) for i in range(len(QUARTERS) - 1)]
    all_rows = []

    for q1, q2 in pairs:
        if q1 not in quarter_to_df or q2 not in quarter_to_df:
            print(f"[SKIP-bias] {source} {q1}_to_{q2} file skip")
            continue

        d1 = quarter_to_df[q1]
        d2 = quarter_to_df[q2]

        merged = pd.merge(d1, d2, on="user_id", how="inner", suffixes=("_q1", "_q2"))
        if merged.empty:
            print(f"[SKIP-bias] {source} {q1}_to_{q2} user")
            continue

        merged["bias_change"] = merged["average_bias_points_q2"] - merged["average_bias_points_q1"]
        merged["quarter1"] = q1
        merged["quarter2"] = q2
        merged["quarter_pair"] = f"{q1}_to_{q2}"

        out = merged[["user_id", "quarter1", "quarter2", "quarter_pair", "bias_change"]].copy()
        all_rows.append(out)
        print(f"[OK-bias] {source} {q1}_to_{q2} common_users={len(out):,}")

    if not all_rows:
        return pd.DataFrame(columns=["user_id", "quarter1", "quarter2", "quarter_pair", "bias_change"])

    bias_df = pd.concat(all_rows, ignore_index=True)
    bias_df["user_id"] = bias_df["user_id"].astype(str)
    bias_df["bias_change"] = pd.to_numeric(bias_df["bias_change"], errors="coerce")
    bias_df = bias_df.dropna(subset=["user_id", "quarter1", "quarter_pair", "bias_change"])
    return bias_df


# --------------------------
# --------------------------
def load_bias_quarter_raw(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    if df.empty:
        return df

    id_col = "user_id" if "user_id" in df.columns else df.columns[0]
    if "total_score" not in df.columns or "appearance_count" not in df.columns:
        raise ValueError(f"biasfilemissing total_score  appearance_count: {file_path}")

    out = df[[id_col, "total_score", "appearance_count"]].copy()
    out.columns = ["user_id", "total_score", "appearance_count"]

    out["user_id"] = out["user_id"].astype(str)
    out["total_score"] = pd.to_numeric(out["total_score"], errors="coerce")
    out["appearance_count"] = pd.to_numeric(out["appearance_count"], errors="coerce")
    out = out.dropna(subset=["total_score", "appearance_count"])
    out = out[out["appearance_count"] > 0]
    return out


def build_total_bias_by_quarter() -> dict:
    quarter_to_df = {}

    for q in QUARTERS:
        parts = []
        for s in SOURCES:
            fp = find_bias_file(s, q)
            if not fp:
                print(f"[WARN-total-bias] missing {s} {q} biasfile skip")
                continue
            print(f"[READ-total-bias] {q} <- {s} / {os.path.basename(fp)}")
            raw = load_bias_quarter_raw(fp)
            if not raw.empty:
                parts.append(raw)

        if not parts:
            print(f"[WARN-total-bias] {q} data")
            quarter_to_df[q] = pd.DataFrame(columns=["user_id", "average_bias_points"])
            continue

        df_all = pd.concat(parts, ignore_index=True)

        agg = df_all.groupby("user_id", as_index=False).agg(
            total_score_sum=("total_score", "sum"),
            appearance_count_sum=("appearance_count", "sum"),
        )
        agg = agg[agg["appearance_count_sum"] > 0].copy()
        agg["average_bias_points"] = agg["total_score_sum"] / agg["appearance_count_sum"]

        quarter_to_df[q] = agg[["user_id", "average_bias_points"]].copy()
        print(f"[OK-total-bias] {q} pooleduser: {len(quarter_to_df[q]):,}")

    return quarter_to_df


def build_bias_change_for_total() -> pd.DataFrame:
    quarter_to_df = build_total_bias_by_quarter()
    pairs = [(QUARTERS[i], QUARTERS[i + 1]) for i in range(len(QUARTERS) - 1)]
    all_rows = []

    for q1, q2 in pairs:
        d1 = quarter_to_df.get(q1, pd.DataFrame())
        d2 = quarter_to_df.get(q2, pd.DataFrame())

        if d1.empty or d2.empty:
            print(f"[SKIP-total-bias] {q1}_to_{q2} pooledquarter skip")
            continue

        merged = pd.merge(d1, d2, on="user_id", how="inner", suffixes=("_q1", "_q2"))
        if merged.empty:
            print(f"[SKIP-total-bias] {q1}_to_{q2} pooleduser")
            continue

        merged["bias_change"] = merged["average_bias_points_q2"] - merged["average_bias_points_q1"]
        merged["quarter1"] = q1
        merged["quarter2"] = q2
        merged["quarter_pair"] = f"{q1}_to_{q2}"

        out = merged[["user_id", "quarter1", "quarter2", "quarter_pair", "bias_change"]].copy()
        all_rows.append(out)
        print(f"[OK-total-bias] {q1}_to_{q2} pooled common_users={len(out):,}")

    if not all_rows:
        return pd.DataFrame(columns=["user_id", "quarter1", "quarter2", "quarter_pair", "bias_change"])

    bias_df = pd.concat(all_rows, ignore_index=True)
    bias_df["user_id"] = bias_df["user_id"].astype(str)
    bias_df["bias_change"] = pd.to_numeric(bias_df["bias_change"], errors="coerce")
    bias_df = bias_df.dropna(subset=["user_id", "quarter1", "quarter_pair", "bias_change"])
    return bias_df


# --------------------------
# --------------------------
def read_openmindness_for_source(source: str) -> pd.DataFrame:
    """Project workflow helper."""
    source_dir = str(rp.openmindness_source_scan_dir(source))
    rows = []

    for folder in POLITICAL_BIAS_FOLDERS:
        folder_path = os.path.join(source_dir, folder)
        if not os.path.isdir(folder_path):
            print(f"[WARN-open] {source} missingfile: {folder_path} skip")
            continue

        for fn in os.listdir(folder_path):
            if not fn.endswith(".csv"):
                continue

            matched_quarter = next((q for q in QUARTERS if fn.startswith(f"{q}_")), None)
            if matched_quarter is None:
                continue

            fp = os.path.join(folder_path, fn)
            try:
                data = pd.read_csv(fp, usecols=["user_id", "appear_count", "average_info_openmindness"])
            except Exception as e:
                print(f"[WARN-open] readcolumn: {fp} | {e}")
                continue

            if data.empty:
                continue

            data["user_id"] = data["user_id"].astype(str)
            data["appear_count"] = pd.to_numeric(data["appear_count"], errors="coerce")
            data["average_info_openmindness"] = pd.to_numeric(data["average_info_openmindness"], errors="coerce")

            data = data[data["appear_count"].fillna(-np.inf) >= APPEAR_COUNT_THRESHOLD]
            data = data.dropna(subset=["average_info_openmindness"])
            if data.empty:
                continue

            out = data[["user_id", "average_info_openmindness"]].copy()
            out["political_bias"] = folder
            out["quarter"] = matched_quarter
            rows.append(out)

    if not rows:
        return pd.DataFrame(columns=["user_id", "average_info_openmindness", "political_bias", "quarter"])

    open_df = pd.concat(rows, ignore_index=True)

    dup_cnt = open_df.duplicated(subset=["user_id", "quarter", "political_bias"]).sum()
    if dup_cnt > 0:
        print(f"[WARN-open] {source} openmindness  = {dup_cnt:,}")

    return open_df


def read_openmindness_for_total() -> pd.DataFrame:
    """Project workflow helper."""
    source_dir = str(rp.openmindness_source_scan_dir("total"))
    rows = []

    for folder in POLITICAL_BIAS_FOLDERS:
        folder_path = os.path.join(source_dir, folder)
        if not os.path.isdir(folder_path):
            print(f"[WARN-open-total] total missingfile: {folder_path} skip")
            continue

        for fn in os.listdir(folder_path):
            if not fn.endswith(".csv"):
                continue

            matched_quarter = next((q for q in QUARTERS if fn.startswith(f"{q}_")), None)
            if matched_quarter is None:
                continue

            fp = os.path.join(folder_path, fn)
            try:
                data = pd.read_csv(fp, usecols=["user_id", "total_appear_count", "average_score"])
            except Exception as e:
                print(f"[WARN-open-total] readcolumn: {fp} | {e}")
                continue

            if data.empty:
                continue

            data["user_id"] = data["user_id"].astype(str)
            data["total_appear_count"] = pd.to_numeric(data["total_appear_count"], errors="coerce")
            data["average_score"] = pd.to_numeric(data["average_score"], errors="coerce")

            data = data[data["total_appear_count"].fillna(-np.inf) >= APPEAR_COUNT_THRESHOLD]
            data = data.dropna(subset=["average_score"])
            if data.empty:
                continue

            out = data[["user_id", "average_score"]].copy()
            out.columns = ["user_id", "average_info_openmindness"]
            out["political_bias"] = folder
            out["quarter"] = matched_quarter
            rows.append(out)

    if not rows:
        return pd.DataFrame(columns=["user_id", "average_info_openmindness", "political_bias", "quarter"])

    open_df = pd.concat(rows, ignore_index=True)

    dup_cnt = open_df.duplicated(subset=["user_id", "quarter", "political_bias"]).sum()
    if dup_cnt > 0:
        print(f"[WARN-open-total] total openmindness  = {dup_cnt:,}")

    return open_df


# ======================
# ======================
def run_regression_for_one_source(source: str) -> pd.DataFrame:
    print(f"\n==============================")
    print(f"process {source}")
    print(f"==============================")

    bias_df = build_bias_change_for_source(source)
    print(f"[CHECK] {source} bias_change row: {len(bias_df):,}")
    print(f"[CHECK] {source} bias_change user summary : {bias_df['user_id'].nunique():,}")
    if not bias_df.empty:
        print("[CHECK] bias_change head ")
        print(bias_df.head(DEBUG_PRINT_HEAD_ROWS).to_string(index=False))
    if bias_df.empty:
        return pd.DataFrame()

    open_df = read_openmindness_for_source(source)
    print(f"[CHECK] {source} openmindness row: {len(open_df):,}")
    print(f"[CHECK] {source} openmindness user summary : {open_df['user_id'].nunique():,}")
    if not open_df.empty:
        print("[CHECK] openmindness head ")
        print(open_df.head(DEBUG_PRINT_HEAD_ROWS).to_string(index=False))
    if open_df.empty:
        return pd.DataFrame()

    merged_df = pd.merge(
        bias_df,
        open_df,
        left_on=["user_id", "quarter1"],
        right_on=["user_id", "quarter"],
        how="inner"
    ).drop(columns=["quarter"])

    print(f"[CHECK] {source} merge row: {len(merged_df):,}")
    print(f"[CHECK] {source} merge user summary : {merged_df['user_id'].nunique():,}")
    if merged_df.empty:
        return pd.DataFrame()

    merged_df["average_info_openmindness"] = pd.to_numeric(merged_df["average_info_openmindness"], errors="coerce")
    merged_df["bias_change"] = pd.to_numeric(merged_df["bias_change"], errors="coerce")
    merged_df = merged_df.dropna(subset=["bias_change", "average_info_openmindness", "political_bias", "quarter_pair"])
    merged_df = merged_df[~merged_df.isin([np.inf, -np.inf]).any(axis=1)]

    if USE_IQR_OUTLIER_FILTER:
        before = len(merged_df)
        merged_df = remove_outliers_iqr(merged_df, "average_info_openmindness")
        merged_df = remove_outliers_iqr(merged_df, "bias_change")
        after = len(merged_df)
        print(f"[CHECK] {source} IQR {before:,} -> {after:,}")

    fixed_quarter_pairs = [f"{QUARTERS[i]}_to_{QUARTERS[i+1]}" for i in range(len(QUARTERS) - 1)]
    fixed_biases = POLITICAL_BIAS_FOLDERS

    results = []
    printed = 0

    for qp in fixed_quarter_pairs:
        for pb in fixed_biases:
            sub = merged_df[(merged_df["quarter_pair"] == qp) & (merged_df["political_bias"] == pb)]
            n = len(sub)

            if DEBUG_PRINT_XY_EXAMPLES and n > 0 and printed < DEBUG_MAX_GROUP_EXAMPLES:
                print(f"\n[EXAMPLE] {source} | {qp} | {pb} | n={n:,}")
                print(sub[["user_id", "average_info_openmindness", "bias_change"]]
                      .head(DEBUG_PRINT_HEAD_ROWS).to_string(index=False))
                printed += 1

            if n < MIN_N_PER_GROUP:
                results.append({
                    "source": source, "quarter_pair": qp, "political_bias": pb,
                    "intercept": np.nan, "slope": np.nan, "p_value": np.nan,
                    "n_obs": n, "rsquared": np.nan, "status": "skipped_n_too_small"
                })
                continue

            X = sm.add_constant(sub[["average_info_openmindness"]])
            y = sub["bias_change"]

            try:
                model = sm.RLM(y, X).fit()
                denom = ((y - y.mean()) ** 2).sum()
                rsq = np.nan if denom == 0 else 1 - (model.resid ** 2).sum() / denom

                results.append({
                    "source": source, "quarter_pair": qp, "political_bias": pb,
                    "intercept": model.params.get("const", np.nan),
                    "slope": model.params.get("average_info_openmindness", np.nan),
                    "p_value": model.pvalues.get("average_info_openmindness", np.nan),
                    "n_obs": n, "rsquared": rsq, "status": "ok"
                })
                print(f"[OK] {source} {qp} {pb} n={n:,} slope={model.params.get('average_info_openmindness', np.nan):.6f}")

            except Exception as e:
                results.append({
                    "source": source, "quarter_pair": qp, "political_bias": pb,
                    "intercept": np.nan, "slope": np.nan, "p_value": np.nan,
                    "n_obs": n, "rsquared": np.nan, "status": f"failed: {e}"
                })
                print(f"[FAIL] {source} {qp} {pb}: {e}")

    res = pd.DataFrame(results)
    out_path = os.path.join(OUT_DIR, f"regression_results_{source}.csv")
    res.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[DONE] save {out_path}  row={len(res)} 35 ")
    return res


# ======================
# ======================
def run_regression_total() -> pd.DataFrame:
    print(f"\n==============================")
    print(f"process TOTAL pooled bias + total openmindness ")
    print(f"==============================")

    bias_df = build_bias_change_for_total()
    print(f"[CHECK] total bias_change row: {len(bias_df):,}")
    print(f"[CHECK] total bias_change user summary : {bias_df['user_id'].nunique():,}")
    if not bias_df.empty:
        print("[CHECK] total bias_change head ")
        print(bias_df.head(DEBUG_PRINT_HEAD_ROWS).to_string(index=False))
    if bias_df.empty:
        return pd.DataFrame()

    open_df = read_openmindness_for_total()
    print(f"[CHECK] total openmindness row: {len(open_df):,}")
    print(f"[CHECK] total openmindness user summary : {open_df['user_id'].nunique():,}")
    if not open_df.empty:
        print("[CHECK] total openmindness head ")
        print(open_df.head(DEBUG_PRINT_HEAD_ROWS).to_string(index=False))
    if open_df.empty:
        return pd.DataFrame()

    merged_df = pd.merge(
        bias_df,
        open_df,
        left_on=["user_id", "quarter1"],
        right_on=["user_id", "quarter"],
        how="inner"
    ).drop(columns=["quarter"])

    print(f"[CHECK] total merge row: {len(merged_df):,}")
    print(f"[CHECK] total merge user summary : {merged_df['user_id'].nunique():,}")
    if merged_df.empty:
        return pd.DataFrame()

    merged_df["average_info_openmindness"] = pd.to_numeric(merged_df["average_info_openmindness"], errors="coerce")
    merged_df["bias_change"] = pd.to_numeric(merged_df["bias_change"], errors="coerce")
    merged_df = merged_df.dropna(subset=["bias_change", "average_info_openmindness", "political_bias", "quarter_pair"])
    merged_df = merged_df[~merged_df.isin([np.inf, -np.inf]).any(axis=1)]

    if USE_IQR_OUTLIER_FILTER:
        before = len(merged_df)
        merged_df = remove_outliers_iqr(merged_df, "average_info_openmindness")
        merged_df = remove_outliers_iqr(merged_df, "bias_change")
        after = len(merged_df)
        print(f"[CHECK] total IQR {before:,} -> {after:,}")

    fixed_quarter_pairs = [f"{QUARTERS[i]}_to_{QUARTERS[i+1]}" for i in range(len(QUARTERS) - 1)]
    fixed_biases = POLITICAL_BIAS_FOLDERS

    results = []
    printed = 0

    for qp in fixed_quarter_pairs:
        for pb in fixed_biases:
            sub = merged_df[(merged_df["quarter_pair"] == qp) & (merged_df["political_bias"] == pb)]
            n = len(sub)

            if DEBUG_PRINT_XY_EXAMPLES and n > 0 and printed < DEBUG_MAX_GROUP_EXAMPLES:
                print(f"\n[EXAMPLE] total | {qp} | {pb} | n={n:,}")
                print(sub[["user_id", "average_info_openmindness", "bias_change"]]
                      .head(DEBUG_PRINT_HEAD_ROWS).to_string(index=False))
                printed += 1

            if n < MIN_N_PER_GROUP:
                results.append({
                    "source": "total", "quarter_pair": qp, "political_bias": pb,
                    "intercept": np.nan, "slope": np.nan, "p_value": np.nan,
                    "n_obs": n, "rsquared": np.nan, "status": "skipped_n_too_small"
                })
                continue

            X = sm.add_constant(sub[["average_info_openmindness"]])
            y = sub["bias_change"]

            try:
                model = sm.RLM(y, X).fit()
                denom = ((y - y.mean()) ** 2).sum()
                rsq = np.nan if denom == 0 else 1 - (model.resid ** 2).sum() / denom

                results.append({
                    "source": "total", "quarter_pair": qp, "political_bias": pb,
                    "intercept": model.params.get("const", np.nan),
                    "slope": model.params.get("average_info_openmindness", np.nan),
                    "p_value": model.pvalues.get("average_info_openmindness", np.nan),
                    "n_obs": n, "rsquared": rsq, "status": "ok"
                })
                print(f"[OK] total {qp} {pb} n={n:,} slope={model.params.get('average_info_openmindness', np.nan):.6f}")

            except Exception as e:
                results.append({
                    "source": "total", "quarter_pair": qp, "political_bias": pb,
                    "intercept": np.nan, "slope": np.nan, "p_value": np.nan,
                    "n_obs": n, "rsquared": np.nan, "status": f"failed: {e}"
                })
                print(f"[FAIL] total {qp} {pb}: {e}")

    res = pd.DataFrame(results)
    out_path = os.path.join(OUT_DIR, "regression_results_total.csv")
    res.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[DONE] save {out_path}  row={len(res)} 35 ")
    return res


def main():
    all_res = []

    for s in SOURCES:
        r = run_regression_for_one_source(s)
        if not r.empty:
            all_res.append(r)

    if all_res:
        stacked = pd.concat(all_res, ignore_index=True)
        stacked_path = os.path.join(OUT_DIR, "regression_results_all_sources_stacked.csv")
        stacked.to_csv(stacked_path, index=False, encoding="utf-8-sig")
        print(f"[DONE] save: {stacked_path}")

    run_regression_total()

    print("\ndone ")





def plot_slope_significance_bubble_chart():
    try:
        plt.style.use('seaborn-v0_8')
    except:
        plt.style.use('ggplot')

    rcParams.update({
        'font.sans-serif': ['SimHei', 'Arial Unicode MS', 'DejaVu Sans'],
        'axes.unicode_minus': False,
        'font.size': 10,
        'axes.labelsize': 11,
        'xtick.labelsize': 9,
        'ytick.labelsize': 10
    })

    def to_plt_color(rgb_str):
        colors = [int(x) / 255.0 for x in rgb_str.replace('rgb(', '').replace(')', '').split(',')]
        return tuple(colors)

    node_color_config = {
        'left': 'rgb(51, 102, 153)',
        'left_leaning': 'rgb(181, 216, 243)',
        'center': 'rgb(240, 230, 140)',
        'right_leaning': 'rgb(255, 153, 153)',
        'right': 'rgb(204, 102, 102)',
        'extreme_right': 'rgb(139, 26, 26)',
    }
    plt_color_map = {k: to_plt_color(v) for k, v in node_color_config.items()}

    file_path = os.path.join(OUT_DIR, "regression_results_total.csv")
    if not os.path.isfile(file_path):
        print(f"[error] regression row main(): {file_path}")
        return

    try:
        df = pd.read_csv(file_path, encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"[error] readfile: {e}")
        return

    for col in ['political_bias', 'quarter_pair']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    for col in ['slope', 'p_value', 'n_obs']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['slope'] = df['slope'] * 1000 

    df = df[df['political_bias'] != 'extreme_left'].copy()
    df = df.dropna(subset=['political_bias', 'slope'])

    quarter_order = [
        '2019_12_2020_01_2020_02_to_2020_03_2020_04_2020_05',
        '2020_03_2020_04_2020_05_to_2020_06_2020_07_2020_08',
        '2020_06_2020_07_2020_08_to_2020_09_2020_10',
        '2020_09_2020_10_to_2020_11_2020_12',
        '2020_11_2020_12_to_2021_01_2021_02'
    ]
    quarter_labels = ['Q1 Q2', 'Q2 Q3', 'Q3 Q4', 'Q4 Q5', 'Q5 Q6']
    bias_order = ['left', 'left_leaning', 'center', 'right_leaning', 'right', 'extreme_right']

    def get_x_pos(row):
        try:
            b_idx = bias_order.index(row['political_bias'])
            q_idx = quarter_order.index(row['quarter_pair'])
            return b_idx + (q_idx - len(quarter_order) / 2 + 0.5) * 0.15
        except:
            return np.nan

    df['x_pos'] = df.apply(get_x_pos, axis=1)
    df = df.dropna(subset=['x_pos'])

    if df.empty:
        print("[warning] data  quarter_pair  ")
        return

    fig, ax = plt.subplots(figsize=(14, 8))

    MIN_BUBBLE_SIZE = 100 
    MAX_BUBBLE_SIZE = 800
    n_min, n_max = df['n_obs'].min(), df['n_obs'].max()

    for i, bias in enumerate(bias_order):
        ax.axvspan(i - 0.5, i + 0.5, facecolor=plt_color_map[bias], alpha=0.18, zorder=0)
        ax.text(i, 0.95, bias.replace('_', ' ').title(), ha='center', va='center', 
                color=plt_color_map[bias], fontweight='bold', fontsize=12,
                transform=ax.get_xaxis_transform())

        subset = df[df['political_bias'] == bias]
        if subset.empty: continue
        
        current_bubble_sizes = np.interp(subset['n_obs'], [n_min, n_max], [MIN_BUBBLE_SIZE, MAX_BUBBLE_SIZE])
        
        ax.scatter(
            subset['x_pos'], subset['slope'],
            s=current_bubble_sizes,
            c=[plt_color_map[bias]],
            alpha=0.9,
            edgecolors='white',
            linewidth=1.0,
            zorder=3
        )

        for _, row in subset.iterrows():
            sig = '*' if row['p_value'] < 0.05 else 'NS'
            ax.text(row['x_pos'], row['slope'], sig,
                    ha='center', va='center', fontsize=8, color='black', fontweight='bold', zorder=4)

    ax.axhline(0, color='#FF9999', linestyle='--', alpha=0.8, linewidth=1.5, zorder=2)
    
    y_max = max(df['slope'].abs().max() * 1.2, 50) 
    ax.set_ylim(-y_max, y_max)
    ax.set_xlim(-0.5, len(bias_order) - 0.5)
    
    ax.grid(axis='y', color='white', linestyle='--', alpha=0.6, zorder=1)
    ax.set_facecolor('#F8F9FA') 
    for spine in ['top', 'right', 'bottom', 'left']:
        ax.spines[spine].set_visible(False)

    all_x_ticks = []
    all_x_labels = []
    for i, _ in enumerate(bias_order):
        for q_idx, q_label in enumerate(quarter_labels):
            pos = i + (q_idx - len(quarter_order) / 2 + 0.5) * 0.15
            all_x_ticks.append(pos)
            all_x_labels.append(q_label)
    
    ax.set_xticks(all_x_ticks)
    ax.set_xticklabels(all_x_labels, rotation=90, fontsize=8)

    ax.set_ylabel('regression (Slope   1000)', labelpad=15, fontweight='bold')

    plt.tight_layout()

    save_path = os.path.join(OUT_DIR, "slope_bubble_final.png")
    plt.savefig(save_path, format="png", dpi=1200, bbox_inches="tight")

    print(f"[done] data: {len(df)}")
    print(f"[done] save: {save_path}")
    plt.show()






if __name__ == "__main__":
    main()
    plot_slope_significance_bubble_chart()
