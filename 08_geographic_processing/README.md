# 08 Geographic Processing

This module adds state-level geography to the media information-consumption workflow. It splits forwarding records by state, attaches user bias, builds state-month 7x7 matrices, combines the three channels, and sums matrices across months.

## Scripts

| Step | Script | Purpose |
| --- | --- | --- |
| 01 | `01_split_forwarding_by_state.py` | Split `output_with_bias` records by state. |
| 02 | `02_add_user_bias_by_state.py` | Add user-bias labels to state-level records. |
| 03 | `03_build_state_bias_crosstabs.py` | Build state-month 7x7 crosstabs. |
| 04 | `04_combine_channels_bias_counts.py` | Combine external, Twitter, and without-URL channels. |
| 05 | `05_sum_bias_counts_across_months.py` | Sum state matrices across months. |
| Pipeline | `run_geo_pipeline.py` | Run the full geographic workflow. |

State input CSV files should be placed in `state/`. Outputs are written under `outputs/geo_information_consume/`.
