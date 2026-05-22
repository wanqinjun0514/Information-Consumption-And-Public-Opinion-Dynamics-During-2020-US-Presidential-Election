# Media Co-Exposure User Sets

This directory builds influenced-user sets for media sources and computes pairwise overlap for network construction.

| Script | Purpose |
| --- | --- |
| `media_step01_extract_retweet_domain_bias.py` | Extract user-media-domain-bias records from monthly external-url forwarding data. |
| `media_step02_build_influenced_user_sets.py` | Build one influenced-user set per media source. |
| `media_step03_pairwise_common_users.py` | Count common influenced users between media sources. |
| `run_media_coexposure.py` | Run the media co-exposure workflow. |
| `media_coexposure_utils.py` | Shared utilities. |
