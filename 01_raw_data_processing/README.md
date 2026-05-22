# 01 Raw Data Processing

This module cleans raw JSON-line Twitter files, merges daily files, and extracts structured CSV records for the downstream scoring pipeline.

## Main Scripts

| Script | Purpose |
| --- | --- |
| `wash_json.py` | Validate JSON lines, remove malformed rows, and merge cleaned files by day. |
| `extract_information_final.py` | Extract tweet, retweet, quote, reply, user, URL, and metadata fields into CSV output. |

## Inputs and Outputs

Raw JSON-line files should be placed in the local raw-data folders used by `wash_json.py`. Extracted CSV files are written under `outputs/us_presidential_output/merge_YYYY_MM/`.

The scripts use `repo_paths.py` for repository-relative paths. Keep large raw files outside Git unless a small sample is intentionally added.
