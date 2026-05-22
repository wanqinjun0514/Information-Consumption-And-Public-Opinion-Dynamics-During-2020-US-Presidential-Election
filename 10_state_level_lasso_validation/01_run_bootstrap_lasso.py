"""Project workflow helper."""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from joblib import Parallel, delayed
from scipy import stats
from sklearn.linear_model import Lasso, LassoCV
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor

_script_dir = Path(__file__).resolve().parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

import lasso_config as lc

lc.init_run(quick="--quick" in sys.argv)
PARAM = lc.PARAM
OUTPUT_DIR = lc.OUTPUT_DIR
resolve_data_csv = lc.resolve_data_csv
print(" ")

# ==========================================
# ==========================================
start_time = time.perf_counter()

# ==========================================
# ==========================================

def get_vif_statsmodels(X_df):
    """Project workflow helper."""
    X_check = X_df.copy()
    if 'const' not in X_check.columns:
        X_check = sm.add_constant(X_check)
    
    vif_data = pd.DataFrame()
    vif_data["Variable"] = X_check.columns
    vif_data["VIF"] = [variance_inflation_factor(X_check.values, i) for i in range(X_check.shape[1])]
    return vif_data[vif_data["Variable"] != 'const']

def backward_elimination(y, X, p_threshold=0.1):
    """Project workflow helper."""
    features = list(X.columns)
    
    while len(features) > 0:
        X_const = sm.add_constant(X[features])
        model = sm.OLS(y, X_const).fit()
        
        p_values = model.pvalues.drop('const', errors='ignore')
        
        if p_values.max() <= p_threshold:
            break
            
        remove_feat = p_values.idxmax()
        print(f"  [] {remove_feat} (P-value={p_values.max():.4f})")
        features.remove(remove_feat)
        
    return model, features

def run_bootstrap_lasso(iter_idx, X_scaled, y, alpha, is_null=False):
    """Project workflow helper."""
    np.random.seed(iter_idx)
    
    n_samples = len(y)
    indices = np.arange(n_samples)
    
    if is_null:
        y_proc = np.random.permutation(y)
        y_use = pd.Series(y_proc, index=indices)
    else:
        y_use = pd.Series(y, index=indices)
        
    train_idx = np.random.choice(indices, size=n_samples, replace=True)
    
    oob_idx = np.array(list(set(indices) - set(train_idx)))
    
    if len(oob_idx) < 3:
        return None

    X_train = X_scaled.iloc[train_idx]
    y_train = y_use.iloc[train_idx]
    X_test = X_scaled.iloc[oob_idx]
    y_test = y_use.iloc[oob_idx]
    
    model_selector = Lasso(alpha=alpha, max_iter=5000)
    model_selector.fit(X_train, y_train)
    
    selected_mask = model_selector.coef_ != 0
    selected_features = X_train.columns[selected_mask].tolist()
    
    res = {
        'iter': iter_idx,
        'is_null': is_null,
        'r2': np.nan,
        'cor': np.nan,
        'coefs': {}
    }
    
    if len(selected_features) > 0:
        X_train_sel = sm.add_constant(X_train[selected_features])
        ols_model = sm.OLS(y_train, X_train_sel).fit()
        
        res['coefs'] = ols_model.params.drop('const', errors='ignore').to_dict()
        
        X_test_sel = sm.add_constant(X_test[selected_features], has_constant='add')
        y_pred = ols_model.predict(X_test_sel)
        
        res['r2'] = r2_score(y_test, y_pred)
        if np.std(y_pred) > 1e-9 and np.std(y_test) > 1e-9:
             res['cor'] = stats.pearsonr(y_test, y_pred)[0]
        else:
             res['cor'] = 0.0
    else:
        mean_pred = np.mean(y_train)
        y_pred = np.full(len(y_test), mean_pred)
        res['r2'] = r2_score(y_test, y_pred)
        res['cor'] = 0.0
        
    return res

# ==========================================
# ==========================================
print("\nprocessingreaddata...")
_csv = resolve_data_csv()
if not _csv.is_file():
    raise FileNotFoundError(
        f" df_combined.csv :\n"
        f"  - {Path(PARAM['file_path']).parent}\n"
        f"   10_state_level_lasso_validation/inputs/df_combined.csv"
    )
df = pd.read_csv(_csv)

all_cols = df.columns
x_cols = all_cols[4:]
y_col_name = 'Y'
df[y_col_name] = df.iloc[:, 3] - df.iloc[:, 2]
diff = df.iloc[:, 3] - df.iloc[:, 2]
df[y_col_name] = np.arcsinh(df.iloc[:, 3] - df.iloc[:, 2])

df['Orig_ID'] = range(len(df))

data_work = df[[y_col_name, "State", 'Orig_ID'] + list(x_cols)].copy()

data_work.replace([np.inf, -np.inf], np.nan, inplace=True)
data_work.dropna(inplace=True)
data_work.reset_index(drop=True, inplace=True)



print("\n--- []  30  ---")

data_sorted = data_work.sort_values(by=y_col_name).reset_index(drop=True)
# data_sorted = data_work
n_total = len(data_sorted)
n_keep = PARAM["n_keep_states"]

if n_total >= n_keep:
    # Start = (50 - 30) // 2 = 10
    start_idx = (n_total - n_keep) // 2
    end_idx = start_idx + n_keep

    # start_idx = 17
    # end_idx = 30
    dropped_head = data_sorted.iloc[:start_idx]
    dropped_tail = data_sorted.iloc[end_idx:]
    
    print(f": {n_total}")
    print(f": {start_idx} - {end_idx - 1} ( Y )")
    print(f" (Low Y, Blue): {len(dropped_head)}  -> {dropped_head['State'].tolist()}")
    print(f" (High Y, Red): {len(dropped_tail)}  -> {dropped_tail['State'].tolist()}")

    data_work = data_sorted.iloc[start_idx:end_idx].reset_index(drop=True)
    
    print(f": {len(data_work)}")
    print(f" Y : {data_work[y_col_name].min():.4f} to {data_work[y_col_name].max():.4f}")
    
else:
    print(f"warning:  ({n_total})  ({n_keep})  ")


# data_work.replace([np.inf, -np.inf], np.nan, inplace=True)
# data_work.dropna(inplace=True)
# data_work.reset_index(drop=True, inplace=True)

# # ==========================================
# # ==========================================

# data_sorted = data_work.sort_values(by=y_col_name).reset_index(drop=True)

# n_total = len(data_sorted)

# if n_total > n_drop:
#     start_drop_idx = (n_total - n_drop) // 2
#     end_drop_idx = start_drop_idx + n_drop
    
#     dropped_samples = data_sorted.iloc[start_drop_idx:end_drop_idx]

#     data_head = data_sorted.iloc[:start_drop_idx]
#     data_tail = data_sorted.iloc[end_drop_idx:]
#     data_work = pd.concat([data_head, data_tail]).reset_index(drop=True)
    
# else:

# ==========================================
# ==========================================
print("\n---  data ---")


# ==========================================
# ==========================================
print("\n---  data ---")

X_raw_all = data_work[x_cols]

# X_prop_all = X_raw_all.div(X_raw_all.sum(axis=1), axis=0)


# ---------------------------------------
EPS = 1e-6

X_raw_all_safe = X_raw_all + EPS

geom_mean = np.exp(np.log(X_raw_all_safe).mean(axis=1))

X_prop_all = np.log(X_raw_all_safe.div(geom_mean, axis=0))
# print(X_prop_all[1:])
# print(X_prop_all[25:])
prop_threshold = PARAM["prop_threshold"]
mean_props = X_prop_all.abs().mean(axis=0)
cols_to_keep = mean_props[mean_props > prop_threshold].index.tolist()

print(f": {len(x_cols)}")
print(f": {len(cols_to_keep)} ( > {prop_threshold})")
print(f": {list(set(x_cols) - set(cols_to_keep))}")

x_cols = cols_to_keep

X_prop_filtered = X_prop_all[x_cols]

# ==========================================
# ==========================================
print("\n---   (Cook's Distance) ---")

X_temp_c = sm.add_constant(X_prop_filtered)
y_temp = data_work[y_col_name]

model_diag = sm.OLS(y_temp, X_temp_c).fit()
influence = model_diag.get_influence()
cooks = influence.cooks_distance[0]
print(cooks)
threshold_val = PARAM['cooks_threshold'] / len(data_work)
outliers_idx = np.where(cooks > threshold_val)[0]

print(f"Cook's Threshold: {threshold_val}",len(outliers_idx))
# print(cooks)

if len(outliers_idx) > 0:
    outlier_states = data_work.loc[outliers_idx, 'State'].tolist()
    outlier_ids = data_work.loc[outliers_idx, 'Orig_ID'].tolist()
    print(f": {outliers_idx}, ID: {outlier_ids}")
    print(f"state_abbrev: {', '.join(outlier_states)}")
    
    data_cleaned = data_work.drop(index=outliers_idx).reset_index(drop=True)
    
    X_prop_final = X_prop_filtered.drop(index=outliers_idx).reset_index(drop=True)
else:
    print(" ")
    data_cleaned = data_work.copy()
    X_prop_final = X_prop_filtered.copy()

print("\n---   (Standardization) ---")
scaler = StandardScaler()

X_scaled = pd.DataFrame(scaler.fit_transform(X_prop_final), columns=x_cols)
# X_scaled = X_prop_final
y_clean = data_cleaned[y_col_name].values



from sklearn.linear_model import LassoCV

pre_model = LassoCV(cv=10, max_iter=50000).fit(X_scaled, y_clean)
alpha_optimal = pre_model.alpha_
print(f" Alpha: {alpha_optimal}")



# ==========================================
# ==========================================
num_cores = max(1, os.cpu_count() - 1)
print(f"\n--- row ( {num_cores} ) ---")

ids_clean = data_cleaned['Orig_ID'].values

print(f"1. row Bootstrap (n={PARAM['n_outer_iter']})...")
real_results = Parallel(n_jobs=num_cores, verbose=5)(
    delayed(run_bootstrap_lasso)(i, X_scaled, y_clean, PARAM['lasso_alpha'], is_null=False) 
    for i in range(PARAM['n_outer_iter'])
)
real_results = [r for r in real_results if r is not None]

real_r2_vals = [r['r2'] for r in real_results]
real_cor_vals = [r['cor'] for r in real_results]
mean_real_r2 = np.mean(real_r2_vals)
mean_real_cor = np.mean(real_cor_vals)

print(f"   ->  R2 (OOB): {mean_real_r2:.4f}")
print(f"   ->  Corr (OOB): {mean_real_cor:.4f}")

if PARAM['n_null_iter'] > 0:
    print(f"2. row (n={PARAM['n_null_iter']})...")
    null_results = Parallel(n_jobs=num_cores, verbose=5)(
        delayed(run_bootstrap_lasso)(i, X_scaled, y_clean, PARAM['lasso_alpha'], is_null=True) 
        for i in range(PARAM['n_null_iter'])
    )
    null_results = [r for r in null_results if r is not None]

    null_r2_vals = [r['r2'] for r in null_results]
    null_cor_vals = [r['cor'] for r in null_results]
else:
    print("2. skip (n_null_iter=0)")
    null_r2_vals, null_cor_vals = [], []

print("rowdone processingdata...")

# ==========================================
# ==========================================
if PARAM['n_null_iter'] > 0:
    print("\n---  summary (Permutation Test) ---")
    print(": P  ")
    
    n_null = len(null_r2_vals)
    count_better_r2 = np.sum(np.array(null_r2_vals) > mean_real_r2)
    p_value_r2 = (count_better_r2 + 1) / (n_null + 1)

    count_better_cor = np.sum(np.array(null_cor_vals) > mean_real_cor)
    p_value_cor = (count_better_cor + 1) / (n_null + 1)

    print(f"R2 P-value: {p_value_r2:.5f}")
    print(f"Correlation P-value: {p_value_cor:.5f}")
else:
    p_value_r2, p_value_cor = np.nan, np.nan

# ==========================================
# ==========================================
print("\n---  save ---")

coef_list = []
coef_dict_all = {} 

for res in real_results:
    row_log = {'Iteration': res['iter']}
    c_map = res['coefs']
    for k, v in c_map.items():
        val = float(v)
        if k not in coef_dict_all:
            coef_dict_all[k] = []
        coef_dict_all[k].append(val)
        row_log[k] = val
    coef_list.append(row_log)

log_df_out = pd.DataFrame(coef_list)

for col in log_df_out.columns:
    if col != 'Iteration':
        log_df_out[col] = pd.to_numeric(log_df_out[col], errors='coerce')

for col in x_cols:
    if col not in log_df_out.columns:
        log_df_out[col] = np.nan
cols_order = ['Iteration'] + list(x_cols)
cols_order = [c for c in cols_order if c in log_df_out.columns]
log_df_out = log_df_out[cols_order]

out_file_raw = os.path.join(OUTPUT_DIR, "Variable_Selection_Raw_Log.csv")
log_df_out.to_csv(out_file_raw, index=False, float_format='%.6f')
print(f"save:\n -> {out_file_raw}")

summary_rows = []
for var, vals in coef_dict_all.items():
    summary_rows.append({
        'Variable': var,
        'Frequency': len(vals),
        'Freq_Pct': len(vals) / len(real_results),
        'Coef_Mean': np.mean(vals),
        'Coef_Median': np.median(vals),
        'Coef_SD': np.std(vals)
    })

summary_df = pd.DataFrame(summary_rows)
if not summary_df.empty:
    summary_df.sort_values(by='Frequency', ascending=False, inplace=True)
    top_df = summary_df.head(PARAM['top_n_show'])
    top_df = top_df.copy()
    top_vars_list = top_df['Variable'].tolist()
    
    if len(top_vars_list) > 0:
        X_top_vif = X_scaled[top_vars_list]
        vif_res_df = get_vif_statsmodels(X_top_vif)
        
        top_df = pd.merge(top_df, vif_res_df, on='Variable', how='left')

    out_file_summary = os.path.join(OUTPUT_DIR, "Variable_Selection_Summary_Stats.csv")
    top_df.to_csv(out_file_summary, index=False)
    print(f"summarysave:\n -> {out_file_summary}")
else:
    print("warning  ")
    top_df = pd.DataFrame(columns=['Variable', 'Frequency'])

# ==========================================
# ==========================================
print("\n" + "="*50)
print("   (Stable & Significant)")
print("="*50)

if not summary_df.empty:
    stable_vars = summary_df[summary_df['Freq_Pct'] > PARAM['freq_threshold']]['Variable'].tolist()
    print(f"1.  > {PARAM['freq_threshold']*100}% : {stable_vars}")
    
    if len(stable_vars) > 0:
        print(f"2. row ( P > {PARAM['p_value_threshold']} )...")
        final_model, final_features = backward_elimination(y_clean, X_scaled[stable_vars], p_threshold=PARAM['p_value_threshold'])
        
        print(f"\n {len(final_features)} : {final_features}")
        
        print("\n" + "-"*30)
        print(" (Final OLS Summary)")
        print(":  P  OLS t-test ")
        print("-" * 30)
        print(final_model.summary())
        
        print("\n" + "-"*30)
        print(" (VIF)")
        print("-" * 30)
        vif_final = get_vif_statsmodels(X_scaled[final_features])
        print(vif_final)
        if vif_final['VIF'].max() > 5:
            print("note:  VIF > 5  ")
        else:
            print("note: VIF   ")
            
        # pd.DataFrame({'Final_Feature': final_features}).to_csv(os.path.join(OUTPUT_DIR, "Final_Selected_Features.csv"), index=False)

        # ==========================================
        # ==========================================
        print("\n--- saveplot ---")
        
        
        model_stats_data = {
            'Metric': [
                'R-squared', 'Adj. R-squared', 'F-statistic', 'Prob (F-stat)', 
                'Log-Likelihood', 'AIC', 'BIC', 'No. Observations', 'Df Residuals', 'Df Model'
            ],
            'Value': [
                final_model.rsquared, final_model.rsquared_adj, final_model.fvalue, final_model.f_pvalue,
                final_model.llf, final_model.aic, final_model.bic, final_model.nobs, final_model.df_resid, final_model.df_model
            ]
        }
        df_model_stats = pd.DataFrame(model_stats_data)

        coef_df = pd.DataFrame({
            'Feature': final_model.params.index,
            'Coefficient': final_model.params.values,
            'Std_Error': final_model.bse.values,
            't_value': final_model.tvalues.values,
            'P_Value': final_model.pvalues.values,
            'CI_Lower': final_model.conf_int()[0].values,
            'CI_Upper': final_model.conf_int()[1].values
        })
        vif_to_merge = vif_final.rename(columns={'Variable': 'Feature'})
        
        df_coef_merged = pd.merge(coef_df, vif_to_merge, on='Feature', how='left')
        is_const = coef_df['Feature'] == 'const'
        df_coef_sorted = pd.concat([
            coef_df[is_const],
            coef_df[~is_const].sort_values(by='P_Value')
        ])

        excel_path = os.path.join(OUTPUT_DIR, "Final_Model_Full_Report.xlsx")
        
        try:
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df_model_stats.to_excel(writer, sheet_name='Model_Performance', index=False)
                
                df_coef_merged.to_excel(writer, sheet_name='Coefficients_and_VIF', index=False)
                
                summary_text = final_model.summary().as_text()
                pd.DataFrame([summary_text]).to_excel(writer, sheet_name='Raw_Summary_Text', index=False, header=['OLS Summary'])
                
            print(f" -> save(Excel): {excel_path}")
            print("    (3Sheet: Model_Performance, Coefficients_and_VIF, Raw_Summary)")
            
        except Exception as e:
            print(f"save Excel  (missing openpyxl ): {e}")
            df_coef_sorted.to_csv(os.path.join(OUTPUT_DIR, "Final_Model_Coefs_Backup.csv"), index=False)

        y_pred_final = final_model.predict()
        y_true_final = y_clean

        fig_final = plt.figure(figsize=(14, 6))
        gs_final = fig_final.add_gridspec(1, 2)

        y_pred_final = final_model.predict()
        y_true_final = y_clean
        
        residuals = y_true_final - y_pred_final
        resid_std = np.std(residuals)

        with sns.axes_style("whitegrid"):
            fig_final = plt.figure(figsize=(15, 7))
            gs_final = fig_final.add_gridspec(1, 2, width_ratios=[1, 1.2])

            # ==========================================
            # ==========================================
            ax_fit = fig_final.add_subplot(gs_final[0, 0])
            
            min_val = min(y_true_final.min(), y_pred_final.min()) - 1
            max_val = max(y_true_final.max(), y_pred_final.max()) + 1
            line_range = np.linspace(min_val, max_val, 100)

            ax_fit.fill_between(line_range, line_range - 2*resid_std, line_range + 2*resid_std,
                                color='gray', alpha=0.15, label='95% Prediction Interval')

            ax_fit.vlines(y_true_final, y_true_final, y_pred_final, 
                          colors='gray', alpha=0.3, linewidth=0.8, zorder=1)

            ax_fit.plot(line_range, line_range, color='#d62728', linestyle='--', linewidth=2, label='Perfect Fit')

            sns.scatterplot(x=y_true_final, y=y_pred_final, 
                            alpha=0.7, color='#1f77b4', edgecolor='white', s=60, 
                            ax=ax_fit, label='Data Points', zorder=2)
            
            ax_fit.text(0.05, 0.95, f'$R^2 = {final_model.rsquared:.3f}$', transform=ax_fit.transAxes, 
                        fontsize=12, fontweight='bold', verticalalignment='top', 
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor='gray'))
            
            ax_fit.set_title("Actual vs Fitted (with Residuals)", fontsize=13)
            ax_fit.set_xlabel("Actual Values (Y)", fontsize=11)
            ax_fit.set_ylabel("Fitted Values ($\hat{Y}$)", fontsize=11)
            ax_fit.legend(loc='lower right', frameon=True)
            ax_fit.set_aspect('equal', adjustable='datalim')

            # ==========================================
            # ==========================================
            plot_df = df_coef_sorted[df_coef_sorted['Feature'] != 'const'].copy()
            plot_df = plot_df.sort_values(by='Coefficient', key=abs, ascending=False)
            
            ax_coef = fig_final.add_subplot(gs_final[0, 1])
            
            if not plot_df.empty:
                colors = ['#c44e52' if c > 0 else '#4c72b0' for c in plot_df['Coefficient']]
                
                error_bar_lengths = 1.96 * plot_df['Std_Error']
                y_pos = np.arange(len(plot_df))
                
                bars = ax_coef.barh(y_pos, plot_df['Coefficient'], xerr=error_bar_lengths, 
                             color=colors, align='center', alpha=0.85, 
                             capsize=5, edgecolor='grey', linewidth=0.8)
                
                ax_coef.set_yticks(y_pos)
                ax_coef.set_yticklabels(plot_df['Feature'], fontsize=10)
                ax_coef.invert_yaxis()
                
                ax_coef.axvline(0, color='black', linewidth=1.2, linestyle='-')
                
                ax_coef.set_title(f"Significant Coefficients (with 95% CI)", fontsize=13)
                ax_coef.set_xlabel("Coefficient Value", fontsize=11)
                
                from matplotlib.patches import Patch
                legend_elements = [Patch(facecolor='#c44e52', alpha=0.85, label='Positive Impact'),
                                   Patch(facecolor='#4c72b0', alpha=0.85, label='Negative Impact')]
                ax_coef.legend(handles=legend_elements, loc='lower right')
                
            else:
                ax_coef.text(0.5, 0.5, "Only Intercept in Model", ha='center', fontsize=12)

            plt.tight_layout()
            final_plot_path = os.path.join(OUTPUT_DIR, "Final_Model_Fit_and_Coefs.png")
            plt.savefig(final_plot_path, dpi=300)
            plt.close()
            print(f" -> save: {final_plot_path}")
    else:
        print("warning:  > 50%   lasso_alpha  freq_threshold ")
else:
    print("  ")

# ==========================================
# ==========================================
print("\n---  plot ---")

if not top_df.empty:
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.9])
    
    # ----------------------------------------------------
    # ----------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    y_pos = np.arange(len(top_df))
    top_vars_ordered = top_df['Variable'][::-1]
    freq_ordered = top_df['Frequency'][::-1]
    
    ax1.barh(y_pos, freq_ordered, color='steelblue', alpha=0.8)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(top_vars_ordered)
    ax1.set_xlabel(f"Selection Count (Total {PARAM['n_outer_iter']})")
    ax1.set_ylabel("Feature Name")
    ax1.set_title(f"Top {len(top_df)} Selection Frequency")
    ax1.axvline(len(real_results) * PARAM['freq_threshold'], color='red', linestyle='--', label='Threshold')
    ax1.legend(loc='lower right')
    
    ax1.text(1.02, 1.0, "Avg Coef\n(incl. 0)", transform=ax1.transAxes, 
             ha='left', va='bottom', fontweight='bold', fontsize=10, color='black')

    for i, var_name in enumerate(top_vars_ordered):
        if var_name in log_df_out.columns:
            g_mean = log_df_out[var_name].fillna(0).mean()
        else:
            g_mean = 0.0
            
        color_text = '#d62728' if g_mean > 0 else '#1f77b4'
        
        ax1.text(1.02, i, f"{g_mean:.4f}", 
                 transform=ax1.get_yaxis_transform(),
                 ha='left', va='center', 
                 color=color_text, fontsize=9, fontweight='bold')

    # ----------------------------------------------------
    # ----------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1], sharey=ax1)
    
    box_data = []
    for v in top_vars_ordered:
        box_data.append(coef_dict_all[v])
    
    bp = ax2.boxplot(box_data, vert=False, patch_artist=True, positions=y_pos, showfliers=False)
    
    for i, box in enumerate(bp['boxes']):
        median_val = np.median(box_data[i])
        if median_val > 0:
            box.set_facecolor('salmon')
            box.set_edgecolor('darkred')
        else:
            box.set_facecolor('skyblue')
            box.set_edgecolor('darkblue')
        box.set_alpha(0.6)
        plt.setp(bp['medians'][i], color='black')

    ax2.set_xlabel("Coefficient Value (When Selected)")
    ax2.set_title("Coef Distribution (Conditional)")
    ax2.axvline(0, color='black', linewidth=1)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(top_vars_ordered)
    
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='salmon', label='Positive'),
        Patch(facecolor='skyblue', label='Negative')
    ]
    ax2.legend(handles=legend_elements, loc='lower right')
    
    # ----------------------------------------------------
    # ----------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 0])
    sns.kdeplot(real_r2_vals, color='red', fill=True, label='Real Model', ax=ax3)
    if PARAM['n_null_iter'] > 0:
        sns.kdeplot(null_r2_vals, color='grey', fill=True, label='Null Model', ax=ax3)
    ax3.axvline(mean_real_r2, color='darkred', linestyle='--', label=f'Mean: {mean_real_r2:.2f}')
    ax3.set_xlim(-1, 1)
    ax3.set_title("R2 Validation")
    ax3.legend()
    
    # ----------------------------------------------------
    # ----------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 1])
    sns.kdeplot(real_cor_vals, color='blue', fill=True, label='Real Model', ax=ax4)
    if PARAM['n_null_iter'] > 0:
        sns.kdeplot(null_cor_vals, color='grey', fill=True, label='Null Model', ax=ax4)
    ax4.axvline(mean_real_cor, color='darkblue', linestyle='--', label=f'Mean: {mean_real_cor:.2f}')
    ax4.set_title("Correlation Validation")
    ax4.legend()
    
    plt.tight_layout()
    png_path = os.path.join(OUTPUT_DIR, "Final_Analysis_Plot.png")
    plt.savefig(png_path, dpi=300)
    plt.close()
    print(f"save:\n -> {png_path}")

    n_vars = len(top_df)
    n_cols = 4
    n_rows = int(np.ceil(n_vars / n_cols))
    
    fig_den, axes = plt.subplots(n_rows, n_cols, figsize=(16, 3 * n_rows))
    axes = axes.flatten()
    
    for i in range(n_vars):
        var_name = top_df.iloc[i]['Variable']
        vals = coef_dict_all[var_name]
        ax = axes[i]
        
        short_name = var_name[:22] + "..." if len(var_name) > 25 else var_name
        median_val = np.median(vals)
        plot_color = 'red' if median_val > 0 else 'blue'
        
        sns.kdeplot(vals, ax=ax, fill=True, color=plot_color, alpha=0.3)
        ax.axvline(0, linestyle='--', color='black', linewidth=1)
        ax.set_title(short_name, fontsize=9)
            
    for j in range(i + 1, len(axes)):
        axes[j].axis('off')
        
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    png_path_density = os.path.join(OUTPUT_DIR, "Top15_Coef_Densities.png")
    plt.savefig(png_path_density, dpi=300)
    plt.close()
    print(f"Top 15 save:\n -> {png_path_density}")

else:
    print("warning  plot ")
# ==========================================
# ==========================================
end_time = time.perf_counter()
duration = end_time - start_time

log_content = f"""
========================================
       regressionrow (Lasso + Bootstrap)
========================================
row: {time.strftime("%Y-%m-%d")}
  : {duration:.2f} 
----------------------------------------
  : {num_cores}
: {PARAM['n_outer_iter']}
  : {PARAM['n_null_iter']}
Lasso Alpha: {PARAM['lasso_alpha']}
Freq Threshold: {PARAM['freq_threshold']}
----------------------------------------
[summary (Method 2)]
 R2    : {mean_real_r2:.4f}
R2 P-value     : {p_value_r2:.5f}

 Cor   : {mean_real_cor:.4f}
Cor P-value    : {p_value_cor:.5f}
========================================
"""

print(log_content)
time_file = os.path.join(OUTPUT_DIR, "Run_Time_Log.txt")
with open(time_file, "w", encoding='utf-8') as f:
    f.write(log_content)
print(f"save:\n -> {time_file}")