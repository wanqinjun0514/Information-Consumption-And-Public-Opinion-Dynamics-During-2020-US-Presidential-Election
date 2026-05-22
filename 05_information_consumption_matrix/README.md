# 05 Information Consumption Matrix

This module builds the media information-consumption matrix used for the heatmap analysis.

## Scripts

| Step | Script | Purpose |
| --- | --- | --- |
| 01 | `01_forwarding_simplify_media_20240904.py` | Extract simplified media forwarding relationships for each input channel. |
| 02 | `02_build_media_consumption_counts.py` | Combine simplified forwarding, monthly user scores, and media labels into monthly 7x7 matrices. |
| 03 | `03_plot_information_consumption_heatmap.py` | Merge monthly matrices and export the heatmap data and image. |

Run Step 01 only after the monthly `three_parts_output` inputs are prepared. Run Step 02 after media scoring outputs exist in `02_bias_scoring/outputs/media_average_rating/`.
