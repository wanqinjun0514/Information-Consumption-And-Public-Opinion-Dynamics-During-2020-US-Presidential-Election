# 02 Bias Scoring

This module scores users by the political bias of media or politician accounts they retweet, quote, or reference. It also builds monthly and quarterly cohorts for Sankey and IdeoP analyses.

## Structure

| Directory | Purpose |
| --- | --- |
| `bias_label` | Media and politician bias label CSV files. |
| `three_parts_output` | Monthly input CSV files split into `external_url`, `twitter_url`, and `without_url`. |
| `01_media_bias_scoring` | Media scoring scripts for the three input channels. |
| `02_politician_bias_scoring` | Politician scoring scripts for the three input channels. |
| `03_quarterly_classification_sankey` | Quarterly cohort merging and Sankey inputs. |
| `04_monthly_crosstabs_sankey` | Monthly crosstabs and new-user Sankey inputs. |

## Key Scripts

| Script | Purpose |
| --- | --- |
| `media_ensure_average_bias_points.py` | Backfill `average_bias_points` in existing monthly media score files. |
| `media_classify_quarterly_users_by_bias.py` | Merge monthly scores into quarterly user-bias cohorts. |
| `01_media_bias_scoring/external url bias media/media_bias.py` | Score users from matched external media domains. |
| `01_media_bias_scoring/twitter com bias/twitter_com_username_bias.py` | Score users from matched Twitter profile URLs. |
| `01_media_bias_scoring/without url/without_url_bias.py` | Score users from matched original-user IDs when no URL is present. |

## Inputs

Place monthly extracted CSV files under `three_parts_output/{external_url|twitter_url|without_url}/output_YYYY_MM/`. Label files in `bias_label` must keep their expected column names.

## Outputs

Media outputs are written to `outputs/media_average_rating/`. Politician outputs are written to `outputs/politician_average_rating/`.
