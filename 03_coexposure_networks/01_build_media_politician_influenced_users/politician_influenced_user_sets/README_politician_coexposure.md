# Politician Co-Exposure User Sets

This directory builds influenced-user sets for politician accounts and computes pairwise overlap for network construction.

| Script | Purpose |
| --- | --- |
| `politician_step01_merge_forwarding_data.py` | Merge forwarding records and attach politician bias labels. |
| `build_politician_influenced_user_sets.py` | Build one influenced-user set per politician. |
| `politician_pairwise_common_users.py` | Count common influenced users between politician pairs. |
| `calculate_common_user_ratios.py` | Compute pairwise overlap ratios. |
| `politician_coexposure_utils.py` | Shared utilities. |
