"""
Central paths for reproducible runs.

Scripts resolve the repository root by walking upward until this file is found,
then import this module for project-relative paths.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

DIR_01 = REPO_ROOT / "01_raw_data_processing"
DIR_02 = REPO_ROOT / "02_bias_scoring"
DIR_03 = REPO_ROOT / "03_coexposure_networks"
DIR_04 = REPO_ROOT / "04_core_networks"
DIR_05 = REPO_ROOT / "05_information_consumption_matrix"
DIR_06 = REPO_ROOT / "06_ideological_permeability"
DIR_07 = REPO_ROOT / "07_ideological_change_regression"
DIR_08 = REPO_ROOT / "08_geographic_processing"
DIR_09 = REPO_ROOT / "09_choropleth_mapping"
DIR_10 = REPO_ROOT / "10_state_level_lasso_validation"

# --- Step 01 ---
DIR_01_OUTPUTS = DIR_01 / "outputs"
DIR_01_EXTRACT_RECORD = DIR_01_OUTPUTS / "extract_record"
DIR_01_PRESIDENTIAL_OUTPUT = DIR_01_OUTPUTS / "us_presidential_output"

# --- Step 02 ---
BIAS_LABEL_DIR = DIR_02 / "bias_label"
THREE_PARTS_OUTPUT = DIR_02 / "three_parts_output"
DIR_02_OUTPUTS = DIR_02 / "outputs"
DIR_02_MEDIA_RATING_ROOT = DIR_02_OUTPUTS / "media_average_rating"
DIR_02_POLITICIAN_RATING_ROOT = DIR_02_OUTPUTS / "politician_average_rating"

MEDIA_BIAS_URL_CSV = BIAS_LABEL_DIR / "media-bias-final-url-cleaned.csv"
MEDIA_BIAS_USERNAME_CSV = BIAS_LABEL_DIR / "media-bias-final-username-display.csv"
POLITICIAN_URL_BIAS_CSV = BIAS_LABEL_DIR / "politician_url_bias-final.csv"
POLITICIAN_USERNAME_CSV = BIAS_LABEL_DIR / "politician_username.csv"
DIR_02_POLITICIAN_INFLUENCE = DIR_02_OUTPUTS / "politician_influence" / "external_url"

# --- Step 03 ---
DIR_03_COEXPOSURE_BUILD = DIR_03 / "01_build_media_politician_influenced_users"
DIR_03_POLITICIAN_COEXPOSURE_SCRIPTS = DIR_03_COEXPOSURE_BUILD / "politician_influenced_user_sets"
DIR_03_MEDIA_COEXPOSURE_SCRIPTS = DIR_03_COEXPOSURE_BUILD / "media_influenced_user_sets"
DIR_03_COEXPOSURE_NETWORK_SCRIPTS = DIR_03 / "02_build_coexposure_networks"

MEDIA_COEXPOSURE_DATA = DIR_03 / "media Co-exposure Networks"
POLITICIAN_INFLUENCED_SETS = DIR_03 / "politician_Co-exposure_Networks" / "influenced_user_sets"
DIR_03_OUTPUTS = DIR_03 / "outputs"
DIR_03_COEXPOSURE_INTERMEDIATE = DIR_03_OUTPUTS / "coexposure_intermediate"
DIR_03_ALL_TYPES_FILTERED = DIR_03_COEXPOSURE_INTERMEDIATE / "all_types_data_filtered"
POLITICIAN_PAIRWISE_EDGES_CSV = DIR_03_COEXPOSURE_INTERMEDIATE / "politician_common_influenced_users_sorted.csv"
COEXPOSURE_RESULT_DIR = DIR_03_OUTPUTS / "coexposure_network_results"
DIR_03_MEDIA_RETWEET_DOMAIN_BIAS = DIR_03_COEXPOSURE_INTERMEDIATE / "retweet_user_id_Domain_bias"
DIR_03_MEDIA_DOMAIN_BIAS_ALL = DIR_03_MEDIA_RETWEET_DOMAIN_BIAS / "all_data.csv"
DIR_03_MEDIA_INFLUENCED_SETS = DIR_03_COEXPOSURE_INTERMEDIATE / "media_influenced_user_sets"
MEDIA_PAIRWISE_EDGES_CSV = DIR_03_COEXPOSURE_INTERMEDIATE / "media_common_influenced_users_sorted.csv"
POLITICIAN_COEXPOSURE_BIAS_CSV = DIR_03_COEXPOSURE_INTERMEDIATE / "combined with screenname and bias.csv"

# --- Step 04 ---
TOP1_PERCENT_NETWORK_DIR = DIR_04 / "Top1Percent_network"
TOP1_PERCENT_HUB_DIR = TOP1_PERCENT_NETWORK_DIR / "quarterly_community_hub_analysis"
FORWARDING_NETWORK_OUTPUT = DIR_04 / "outputs" / "forwarding_network"
TOP2_PERCENT_DEGREE_DIR = FORWARDING_NETWORK_OUTPUT / "quarter_Top2Percent_degree"
TOP2_PERCENT_HUB_DIR = TOP2_PERCENT_DEGREE_DIR / "quarterly_community_hub_analysis"
BEST_K_CORE_DIR = FORWARDING_NETWORK_OUTPUT / "quarter_best_k_core"
BEST_K_HUB_DIR = BEST_K_CORE_DIR / "quarterly_community_hub_analysis"
BEST_K_COMMUNITY_SPLIT_DIR = BEST_K_CORE_DIR / "quarterly_community_split_and_hub_analysis"
FULL_MERGE_K_SCAN_DIR = FORWARDING_NETWORK_OUTPUT / "full_merge_k_scan" / "per_month"
FULL_MERGE_K_ROOT = FORWARDING_NETWORK_OUTPUT / "full_merge_k_scan"
QUARTER_MERGE_K_SCAN_DIR = FORWARDING_NETWORK_OUTPUT / "quarter_merge_k_scan"

TOTAL_URL_POLITICIAN_BIAS_QUARTER = (
    DIR_02_OUTPUTS / "politician_average_rating" / "total_url-rating" / "user_bias_scores_by_quarter"
)
TOTAL_URL_MEDIA_BIAS_QUARTER = (
    DIR_02_OUTPUTS / "media_average_rating" / "total_url-rating" / "user_bias_scores_by_quarter"
)
KEYWORD_COV_EXTERNAL_DIR = FORWARDING_NETWORK_OUTPUT / "keyword_covid_external"

# --- Step 05 ---
DIR_05_OUTPUTS = DIR_05 / "outputs"
SIMPLIFIED_FORWARDING_MEDIA_ROOT = DIR_05_OUTPUTS / "Simplyfied_Forwarding_relationship_Media"
SIMPLIFIED_FORWARDING_MEDIA_EXTERNAL = SIMPLIFIED_FORWARDING_MEDIA_ROOT / "external_url"
SIMPLIFIED_FORWARDING_MEDIA_TWITTER = SIMPLIFIED_FORWARDING_MEDIA_ROOT / "twitter_url"
SIMPLIFIED_FORWARDING_MEDIA_WITHOUT = SIMPLIFIED_FORWARDING_MEDIA_ROOT / "without_url"
INFORMATION_CONSUME_MEDIA_ROOT = DIR_05_OUTPUTS / "Information_Consume" / "Media"
MEDIA_EXTERNAL_INFORMATION_CONSUME = INFORMATION_CONSUME_MEDIA_ROOT / "Media_external_information_consume"
MEDIA_TWITTER_INFORMATION_CONSUME = INFORMATION_CONSUME_MEDIA_ROOT / "Media_twitter_information_consume"
MEDIA_WITHOUT_INFORMATION_CONSUME = INFORMATION_CONSUME_MEDIA_ROOT / "Media_without_information_consume"
MERGED_CONSUMPTION_MATRIX_CSV = INFORMATION_CONSUME_MEDIA_ROOT / "Merged_Cleaned_Consumption_Matrix.csv"
FIGURE_4A_HEATMAP_PNG = INFORMATION_CONSUME_MEDIA_ROOT / "Figure_4a_Heatmap_LogScale.png"
OUTPUT_WITH_BIAS_MEDIA_ROOT = DIR_05_OUTPUTS / "output_with_bias_Media"


def media_monthly_user_bias_csv(part: str, month: str) -> Path:
    """Return a monthly media user-bias score CSV path."""
    return DIR_02_MEDIA_RATING_ROOT / f"{part}-rating" / f"user_bias_scores_{month}.csv"


def media_rating_part_dir(part: str) -> Path:
    """Return the media rating directory for one source part."""
    if not part.endswith("_url"):
        part = f"{part}_url"
    return DIR_02_MEDIA_RATING_ROOT / f"{part}-rating"


def media_part_short(part: str) -> str:
    """Return the short source-part name used by IdeoP outputs."""
    return part.replace("_url", "") if part.endswith("_url") else part


def media_quarter_cohort_csv(part: str, quarter: str, user_bias: str) -> Path:
    return media_rating_part_dir(part) / "user_bias_scores_by_quarter" / user_bias / f"{quarter}_{user_bias}_user.csv"


def output_with_bias_media_dir(part: str) -> Path:
    if not part.endswith("_url"):
        part = f"{part}_url"
    return OUTPUT_WITH_BIAS_MEDIA_ROOT / part


def output_with_bias_monthly_csv(part: str, month: str) -> Path:
    return output_with_bias_media_dir(part) / f"output_with_bias_{month}.csv"


# --- Step 06 ---
DIR_06_OUTPUTS = DIR_06 / "outputs"
OPENMINDNESS_MEDIA_ROOT = DIR_06_OUTPUTS / "openmindness" / "media"
OPENMINDNESS_CONTINUOUS = OPENMINDNESS_MEDIA_ROOT / "continuous"
OPENMINDNESS_CONTINUOUS_TOTAL = OPENMINDNESS_CONTINUOUS / "total"
DIR_06_REGRESSION_OUTPUT = DIR_06_OUTPUTS / "regression_outputs"
DIR_06_PLOT_DATA = DIR_06_OUTPUTS / "plot_data"
PLOT_DATA_ALL_SOURCES_RAW_CSV = DIR_06_PLOT_DATA / "plot_data_all_sources_raw.csv"
DIR_06_RIDGE_PLOTS = DIR_06_OUTPUTS / "plots_ridgeline_from_csv"
MEDIA_SANKEY_COMMON_USER_BIAS = (
    DIR_02_MEDIA_RATING_ROOT / "total_url-rating" / "sankey_plot" / "every_quarter" / "common_user_bias"
)


def openmindness_continuous_part_dir(part: str) -> Path:
    return OPENMINDNESS_CONTINUOUS / media_part_short(part)


def openmindness_continuous_score_csv(part: str, user_bias: str, quarter: str) -> Path:
    return openmindness_continuous_part_dir(part) / user_bias / f"{quarter}_{user_bias}_user_info_consumption_openmindness_score.csv"


def openmindness_continuous_total_score_csv(user_bias: str, quarter: str) -> Path:
    return OPENMINDNESS_CONTINUOUS_TOTAL / user_bias / f"{quarter}_{user_bias}_user_info_consumption_openmindness_score.csv"


def openmindness_source_scan_dir(source: str) -> Path:
    """Return the source directory scanned when building plot/regression inputs."""
    if source == "total":
        return OPENMINDNESS_CONTINUOUS_TOTAL
    return openmindness_continuous_part_dir(source)


def three_parts_month_dirs(month: str) -> tuple[str, str, str]:
    """Return twitter, without-url, and external-url input folders for one month."""
    return (
        str(THREE_PARTS_OUTPUT / "twitter_url" / f"output_{month}"),
        str(THREE_PARTS_OUTPUT / "without_url" / f"output_{month}"),
        str(THREE_PARTS_OUTPUT / "external_url" / f"output_{month}"),
    )


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


# --- Step 08 ---
GEO_STATE_INPUT_DIR = DIR_08 / "state"
DIR_08_OUTPUTS = DIR_08 / "outputs"
GEO_INFORMATION_CONSUME_ROOT = DIR_08_OUTPUTS / "geo_information_consume"
GEO_MEDIA_PARTS = ("external_url", "twitter_url", "without_url")


def geo_consume_part_root(part: str) -> Path:
    if not part.endswith("_url"):
        part = f"{part}_url"
    return GEO_INFORMATION_CONSUME_ROOT / part


def geo_by_state_dir(part: str) -> Path:
    """Return Step 01 state-split output directory."""
    return geo_consume_part_root(part) / "by_state"


def geo_with_user_bias_dir(part: str) -> Path:
    """Return Step 02 state records with user-bias labels."""
    return geo_consume_part_root(part) / "with_user_bias"


def geo_bias_counts_dir(part: str) -> Path:
    """Return Step 03 state-month 7x7 matrix directory."""
    return geo_consume_part_root(part) / "bias_counts"


GEO_COMBINED_BIAS_COUNTS_DIR = GEO_INFORMATION_CONSUME_ROOT / "combined_three_channels" / "bias_counts"
GEO_SUM_BIAS_COUNTS_DIR = GEO_INFORMATION_CONSUME_ROOT / "combined_three_channels" / "sum_across_months"

# --- Step 09 ---
DIR_09_OUTPUTS = DIR_09 / "outputs"
STATE_USER_BIAS_PROPORTION_CSV = DIR_09 / "all time every state user bias proportion.csv"
FIGURE_US_STATE_MAP_HTML = DIR_09_OUTPUTS / "Figure_US_states_choropleth_20260420.html"
FIGURE_US_STATE_MAP_PDF = DIR_09_OUTPUTS / "Figure_US_states_choropleth.pdf"

# --- Step 10 ---
DIR_10_INPUTS = DIR_10 / "inputs"
DIR_10_OUTPUTS = DIR_10 / "outputs"
LASSO_BOOTSTRAP_OUTPUT_DIR = DIR_10_OUTPUTS / "lasso_bootstrap"
DIR_10_PLOTS = DIR_10_OUTPUTS / "plots"
LASSO_FINAL_MODEL_EXCEL = LASSO_BOOTSTRAP_OUTPUT_DIR / "Final_Model_Full_Report.xlsx"
RED_BLUE_REGRESSION_PNG = LASSO_BOOTSTRAP_OUTPUT_DIR / "Red_Blue_State_Regression_Plot.png"
STATE_UMAP_PNG = DIR_10_PLOTS / "State_UMAP_Analysis.png"


def resolve_df_combined_csv() -> Path:
    """Return the preferred state-level model input table."""
    for candidate in (DIR_10_INPUTS / "df_combined.csv", DIR_10 / "df_combined.csv"):
        if candidate.is_file():
            return candidate
    return DIR_10_INPUTS / "df_combined.csv"
