# 06 Ideological Permeability

This module computes continuous IdeoP scores for users based on the distance between user bias and consumed media bias. It also builds ridgeline plot data from the computed scores.

## Scripts

| Step | Script | Purpose |
| --- | --- | --- |
| 01 | `01_build_output_with_bias_media.py` | Join simplified forwarding records with media labels and monthly user bias scores. |
| 02 | `02_calculate_information_openness.py` | Compute continuous IdeoP by channel and merge the three channels into `total`. |
| 03 | `03_build_ridgeline_plot_data.py` | Scan IdeoP outputs and build `plot_data_all_sources_raw.csv`. |
| 04 | `04_plot_ridgeline_from_plot_csv.py` | Plot ridgeline distributions from the combined plot-data CSV. |

Outputs are written under `outputs/openmindness/media/continuous/`, `outputs/plot_data/`, and `outputs/plots_ridgeline_from_csv/`.
