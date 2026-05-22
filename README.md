# Political Information Consumption Analysis Pipeline

This repository contains a 10-part Python analysis pipeline for Twitter political communication research. The workflow starts from raw JSON extraction and ends with information-consumption matrices, ideological permeability analysis, state-level geographic summaries, choropleth maps, and Lasso validation.

All project paths are resolved through `repo_paths.py`, so the repository can be cloned to a different drive without editing hard-coded absolute paths.

## Repository Modules

| Module | Directory | Purpose |
| --- | --- | --- |
| 01 | `01_raw_data_processing` | Clean raw JSON lines, merge daily files, and extract structured CSV files. |
| 02 | `02_bias_scoring` | Score media and politician exposure by month and build user bias cohorts. |
| 03 | `03_coexposure_networks` | Build media and politician influenced-user sets and co-exposure networks. |
| 04 | `04_core_networks` | Extract top-degree core networks and analyze Louvain communities. |
| 05 | `05_information_consumption_matrix` | Build 7x7 information-consumption matrices and the heatmap output. |
| 06 | `06_ideological_permeability` | Compute continuous IdeoP scores and build ridgeline plot data. |
| 07 | `07_ideological_change_regression` | Regress bias change on IdeoP and create significance plots. |
| 08 | `08_geographic_processing` | Split forwarding data by state and build state-month 7x7 matrices. |
| 09 | `09_choropleth_mapping` | Build and plot state-level left/right user bias proportions. |
| 10 | `10_state_level_lasso_validation` | Run state-level Lasso, bootstrap validation, regression plots, and UMAP. |

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Python 3.10+ is recommended. Some plotting outputs require optional packages such as `kaleido` or `joypy`.

## Path Convention

Scripts locate the repository root by walking upward until `repo_paths.py` is found, then import shared paths from that module. For new scripts, reuse `repo_paths.py` instead of adding absolute drive paths.

## Typical Run Order

1. Run `01_raw_data_processing` to create monthly extracted CSV files.
2. Run the media and politician scoring scripts in `02_bias_scoring`.
3. Run `05_information_consumption_matrix` to build consumption matrices.
4. Run `06_ideological_permeability` to compute IdeoP and plot data.
5. Run `07_ideological_change_regression` for the regression analysis.
6. Run `08_geographic_processing`, `09_choropleth_mapping`, and `10_state_level_lasso_validation` for geographic and state-level analyses.
7. Run `03_coexposure_networks` and `04_core_networks` when network outputs are needed.

## Data Notes

Large raw Twitter files and full monthly intermediate CSV files are not required to be stored in Git. Place local inputs under the module paths documented in each module README, then run the scripts from the repository root or from the relevant module directory.
