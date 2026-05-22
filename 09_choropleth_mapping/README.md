# 09 Choropleth Mapping

This module computes and plots state-level left/right user-bias proportions for a US choropleth map.

## Data

| File | Purpose |
| --- | --- |
| `all time every state user bias proportion.csv` | State-level bias proportions and normalized plotting scores. |
| `08_geographic_processing/state/{State}.csv` | Optional state input used when rebuilding the proportion CSV. |

## Scripts

| Step | Script | Purpose |
| --- | --- | --- |
| 00 | `00_build_state_user_bias_proportion.py` | Rebuild the state user-bias proportion CSV from state membership and monthly scoring outputs. |
| 01 | `01_plot_us_state_choropleth.py` | Export the US state choropleth map. |

The default HTML output is `outputs/Figure_US_states_choropleth_20260420.html`. PDF export requires `kaleido`.
