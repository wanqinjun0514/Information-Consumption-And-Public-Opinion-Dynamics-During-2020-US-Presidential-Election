# 10 State-Level Lasso Validation

This module runs state-level Lasso and bootstrap validation, then produces regression and UMAP outputs for state-level analysis.

## Scripts

| Script | Purpose |
| --- | --- |
| `run_lasso_pipeline.py` | Run the full state-level validation workflow. |
| `01_run_bootstrap_lasso.py` | Fit bootstrap Lasso models and export model reports. |
| `02_plot_red_blue_regression.py` | Plot red/blue state regression output. |
| `03_state_umap_analysis.py` | Run UMAP on state-level features. |
| `lasso_config.py` | Shared configuration. |

Place the main state-level table at `inputs/df_combined.csv`. Use `--quick` for a small validation run before running the full bootstrap configuration.
