import pandas as pd
import networkx as nx
import community.community_louvain as community_louvain
import os
import numpy as np
import traceback
import sys
from pathlib import Path as _PathLouvain

_rp = _PathLouvain(__file__).resolve()
for _ in range(10):
    if (_rp / "repo_paths.py").exists():
        if str(_rp) not in sys.path:
            sys.path.insert(0, str(_rp))
        break
    _rp = _rp.parent
else:
    raise RuntimeError("Repository root not found; repo_paths.py is missing.")
import repo_paths as _RP

TOP1_PCT_EDGES_ROOT = str(_RP.TOP1_PERCENT_NETWORK_DIR)
TOP1_PCT_HUB_ROOT = str(_RP.TOP1_PERCENT_HUB_DIR)
POLITICIAN_BIAS_Q = str(_RP.TOTAL_URL_POLITICIAN_BIAS_QUARTER)
MEDIA_BIAS_Q = str(_RP.TOTAL_URL_MEDIA_BIAS_QUARTER)
KEYWORD_COV_DIR = str(_RP.KEYWORD_COV_EXTERNAL_DIR)

DEFAULT_LOUVAIN_RESOLUTION = 1.0
DEFAULT_LOUVAIN_SEED = 42


def _top1pct_default_quarters():
    return [
        "2019_12_2020_01_2020_02",
        "2020_03_2020_04_2020_05",
        "2020_06_2020_07_2020_08",
        "2020_09_2020_10",
        "2020_11_2020_12",
        "2021_01_2021_02",
    ]


# =============================================================================
#   {TOP1_PCT_EDGES_ROOT}/{period}_top1pct_edges.csv
#   {TOP1_PCT_EDGES_ROOT}/{period}_top1pct_nodes.csv
#   {period}_res1.0_seed42.gexf
#   {period}_res1.0_seed42_top10_nodes.csv
#   {period}_res1.0_seed42_top3_community_metrics.csv
# =============================================================================
def process_quarterly_analysis_without_diameter_top1_percent(period, base_root=TOP1_PCT_HUB_ROOT, resolution=1.0, random_seed=42):
    """Project workflow helper."""
    edges_base_dir = TOP1_PCT_EDGES_ROOT
    edges_path = os.path.join(edges_base_dir, f"{period}_top1pct_edges.csv")

    period_folder = os.path.join(base_root, period)
    os.makedirs(period_folder, exist_ok=True)

    nodes_path = os.path.join(edges_base_dir, f"{period}_top1pct_nodes.csv")

    params_tag = f"res{resolution}_seed{random_seed}"
    output_gexf = os.path.join(period_folder, f"{period}_{params_tag}.gexf")
    output_top10 = os.path.join(period_folder, f"{period}_{params_tag}_top10_nodes.csv")
    output_comm_metrics = os.path.join(period_folder, f"{period}_{params_tag}_top3_community_metrics.csv")

    print(f"\n" + "=" * 50)
    print(f"processingprocessquarter: {period}")
    print(f"readpath: {period_folder}")

    if not os.path.exists(edges_path) or not os.path.exists(nodes_path):
        if not os.path.exists(edges_path):
            print(f"skip file path: {edges_path}")
        if not os.path.exists(nodes_path):
            print(f"skip file path: {nodes_path}")
        return

    df_edges = pd.read_csv(edges_path)
    df_nodes_attr = pd.read_csv(nodes_path)

    df_edges.columns = ['source', 'target', 'weight'] + list(df_edges.columns[3:])

    G = nx.from_pandas_edgelist(df_edges, 'source', 'target', edge_attr='weight', create_using=nx.DiGraph())

    df_nodes_attr = df_nodes_attr.rename(columns={'community_id': 'original_community'})
    node_attr_dict = df_nodes_attr.set_index('user_id').to_dict('index')
    nx.set_node_attributes(G, node_attr_dict)

    print("row Louvain ...")
    G_undirected = G.to_undirected()
    partition = community_louvain.best_partition(
        G_undirected, weight='weight', resolution=resolution, random_state=random_seed
    )
    nx.set_node_attributes(G, partition, 'louvain_community')

    total_nodes = len(G.nodes())
    counts = pd.Series(partition).value_counts()
    stats = pd.DataFrame({
        'louvain_community': counts.index,
        'node_count': counts.values,
        'percentage (%)': (counts.values / total_nodes * 100).round(2)
    }).sort_values('node_count', ascending=False)

    print("\n[ (Top 5)]:")
    print(stats.head(5).to_string(index=False))

    print("...")
    nx.set_node_attributes(G, dict(G.degree(weight='weight')), 'weighted_degree')
    nx.set_node_attributes(G, nx.pagerank(G, weight='weight'), 'pagerank')

    nodes_data = []
    for node, attrs in G.nodes(data=True):
        row = {'user_id': node}
        row.update(attrs)
        nodes_data.append(row)
    df_full_nodes = pd.DataFrame(nodes_data)

    top_list = []
    for comm_id in stats['louvain_community']:
        comm_df = df_full_nodes[df_full_nodes['louvain_community'] == comm_id]
        t1 = comm_df.nlargest(10, 'weighted_degree').copy()
        t1['ranking_type'] = 'weighted_degree'
        t2 = comm_df.nlargest(10, 'pagerank').copy()
        t2['ranking_type'] = 'pagerank'
        top_list.extend([t1, t2])

    # ==============================================================================
    # ==============================================================================
    print(" Top3  (Exact metrics)...")
    top3_ids = stats['louvain_community'].head(3).tolist()
    comm_metrics_list = []

    for rank, comm_id in enumerate(top3_ids, 1):
        print(f"  ->  {rank}  (ID: {comm_id})...")

        nodes_in_comm = [n for n, c in partition.items() if c == comm_id]
        H = G.subgraph(nodes_in_comm).copy()
        H_und = H.to_undirected()

        num_nodes = len(H.nodes())
        num_edges = len(H.edges())

        density = nx.density(H)

        avg_degree = num_edges / num_nodes if num_nodes > 0 else 0

        try:
            assortativity = nx.degree_assortativity_coefficient(H)
        except Exception:
            assortativity = np.nan

        try:
            clustering_coeff = nx.average_clustering(H_und)
        except Exception:
            clustering_coeff = 0

        comm_metrics_list.append({
            'period': period,
            'rank': rank,
            'community_id': comm_id,
            'node_count': num_nodes,
            'edge_count': num_edges,
            'density': round(density, 8),
            'avg_degree': round(avg_degree, 4),
            'assortativity': round(assortativity, 4) if pd.notna(assortativity) else None,
            'clustering_coefficient': round(clustering_coeff, 4)
        })

    pd.DataFrame(comm_metrics_list).to_csv(output_comm_metrics, index=False, encoding='utf-8-sig')
    print(f"  -> Top3 save: {output_comm_metrics}")
    # ==============================================================================

    pd.concat(top_list).to_csv(output_top10, index=False, encoding='utf-8-sig')

    output_partition_csv = os.path.join(period_folder, f"{period}_top1pct_community_detection_results.csv")
    df_partition_export = df_full_nodes.rename(columns={"louvain_community": "community_id"})
    df_partition_export.to_csv(output_partition_csv, index=False, encoding="utf-8-sig")
    print(f"  -> community_detection_resultssave: {output_partition_csv}")

    print("processingsave GEXF...")
    nx.write_gexf(G, output_gexf)
    print(f"process quarterfile ")


_GEXF_ATTR_TO_CSV = {
    "politician_bias": "politician_bias",
    "media_bias": "media_bias",
    "politician_ideology": "politician_bias_category",
    "media_ideology": "media_bias_category",
}
_CSV_ATTR_TO_GEXF = {v: k for k, v in _GEXF_ATTR_TO_CSV.items()}


def _normalize_node_attr_keys_from_gexf(attr: dict) -> dict:
    out = dict(attr)
    for gexf_key, csv_key in _GEXF_ATTR_TO_CSV.items():
        if gexf_key in out and csv_key not in out:
            out[csv_key] = out[gexf_key]
    return out


def _nodes_dataframe_from_top1pct_gexf(gexf_path, community_attr_candidates=("louvain_community", "community_id")):
    """Project workflow helper."""
    if not os.path.exists(gexf_path):
        raise FileNotFoundError(gexf_path)
    G = nx.read_gexf(gexf_path)
    rows = []
    for n, attrs in G.nodes(data=True):
        uid = str(n).strip()
        if not uid:
            continue
        attr = _normalize_node_attr_keys_from_gexf(dict(attrs))
        comm = None
        for key in community_attr_candidates:
            if key in attr:
                comm = attr.pop(key)
                break
        row = {"user_id": uid, "community_id": comm}
        row.update(attr)
        rows.append(row)
    if not rows:
        raise ValueError(f"GEXF : {gexf_path}")
    df = pd.DataFrame(rows)
    if "community_id" in df.columns:
        df["community_id"] = pd.to_numeric(df["community_id"], errors="coerce")
    df["user_id"] = df["user_id"].astype(str).str.strip()
    return df


def _load_nodes_community_media_bias(
    period_folder,
    gexf_params_tag="res1.0_seed42",
    completed_csv_template="{quarter}_top1pct_community_detection_results_classified.csv",
):
    """Project workflow helper."""
    period = os.path.basename(period_folder.rstrip("\\/"))
    csv_path = os.path.join(period_folder, completed_csv_template.format(quarter=period))
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype={"user_id": str})
        df.columns = df.columns.str.strip()
        if {"user_id", "community_id", "media_bias"}.issubset(df.columns):
            df["user_id"] = df["user_id"].astype(str).str.strip()
            df["community_id"] = pd.to_numeric(df["community_id"], errors="coerce")
            df["media_bias"] = pd.to_numeric(df["media_bias"], errors="coerce")
            if df["media_bias"].notna().any():
                return df[["user_id", "community_id", "media_bias"]]

    gexf_path = os.path.join(
        period_folder, f"{period}_{gexf_params_tag}_with_political_attributes.gexf"
    )
    if os.path.exists(gexf_path):
        nodes_df = _nodes_dataframe_from_top1pct_gexf(
            gexf_path,
            community_attr_candidates=("louvain community", "louvain_community", "community_id"),
        )
        if "media_bias" in nodes_df.columns:
            nodes_df["media_bias"] = pd.to_numeric(nodes_df["media_bias"], errors="coerce")
            if nodes_df["media_bias"].notna().any():
                return nodes_df[["user_id", "community_id", "media_bias"]]

    return None


def _bias_lookup_dict_from_table(df, id_col_candidates, score_col="average_bias_points"):
    """Project workflow helper."""
    if df is None or df.empty:
        return {}
    df = df.copy()
    df.columns = df.columns.str.strip()
    if score_col not in df.columns:
        return {}
    id_col = next((c for c in id_col_candidates if c in df.columns), None)
    if id_col is None:
        return {}
    out = {}
    for uid, val in zip(df[id_col], df[score_col]):
        if pd.isna(uid):
            continue
        key = str(uid).strip()
        if not key or key.lower() == "nan":
            continue
        out[key] = val
    return out


# =============================================================================
# =============================================================================
def append_quarterly_bias_scores_to_community_nodes_top1_percent(
    periods=None,
    node_base_dir=TOP1_PCT_HUB_ROOT,
    politician_dir=POLITICIAN_BIAS_Q,
    media_dir=MEDIA_BIAS_Q,
    partition_csv_template="{quarter}_top1pct_community_detection_results.csv",
    bias_csv_template="quarterly_user_bias_scores_{quarter}.csv",
    partition_source="csv",
    gexf_params_tag="res1.0_seed42",
    gexf_filename_template="{quarter}_{params_tag}.gexf",
):
    """Project workflow helper."""
    if periods is None:
        periods = _top1pct_default_quarters()
    if partition_source not in ("csv", "gexf", "auto"):
        raise ValueError("partition_source  'csv' 'gexf'  'auto'")

    for quarter_name in periods:
        print(f"\n{'='*40}")
        print(f"processingprocess: {quarter_name}")

        current_node_dir = os.path.join(node_base_dir, quarter_name)
        node_file_path = os.path.join(current_node_dir, partition_csv_template.format(quarter=quarter_name))
        gexf_path = os.path.join(
            current_node_dir,
            gexf_filename_template.format(quarter=quarter_name, params_tag=gexf_params_tag),
        )

        df_node = None
        try:
            if partition_source in ("csv", "auto") and os.path.exists(node_file_path):
                print(f"  -> read CSV: {os.path.basename(node_file_path)}")
                df_node = pd.read_csv(node_file_path, encoding="utf-8-sig", dtype={"user_id": str})
                df_node.columns = df_node.columns.str.strip()
            elif partition_source == "csv":
                print(f"  [skip]  csv file: {node_file_path}")
                continue

            if df_node is None and partition_source in ("gexf", "auto"):
                if os.path.exists(gexf_path):
                    print(f"  ->  GEXF   Louvain : {os.path.basename(gexf_path)}")
                    df_node = _nodes_dataframe_from_top1pct_gexf(gexf_path)
                elif partition_source == "gexf":
                    print(f"  [skip]  gexf file: {gexf_path}")
                    continue

            if df_node is None:
                print(
                    f"  [skip]  CSV: {node_file_path}\n"
                    f"         GEXF: {gexf_path}\n"
                    f"          partition_source='gexf'  gexf_params_tag  "
                )
                continue

            if "user_id" not in df_node.columns:
                raise ValueError(f"missingcolumn user_id column: {list(df_node.columns)}")

            df_node["user_id"] = df_node["user_id"].astype(str).str.strip()
            if "community_id" in df_node.columns:
                n_miss = int(df_node["community_id"].isna().sum())
                if n_miss:
                    print(f"  [warning]  {n_miss} rowmissing community_id  GEXF/CSV  Louvain ")
            df_node["politician_bias"] = np.nan
            df_node["media_bias"] = np.nan

            pol_file_path = os.path.join(
                politician_dir, bias_csv_template.format(quarter=quarter_name)
            )
            pol_bias_dict = {}
            if os.path.exists(pol_file_path):
                print(f"  -> readpoliticianBias: {os.path.basename(pol_file_path)}")
                df_pol = pd.read_csv(pol_file_path, encoding="utf-8-sig", dtype=str)
                pol_bias_dict = _bias_lookup_dict_from_table(
                    df_pol, ("retweeted_user_id", "user_id")
                )
                if not pol_bias_dict:
                    print(f"  [error] politician column: {list(df_pol.columns)}")
            else:
                print(f"  [warning] politicianfile: {pol_file_path}")

            media_file_path = os.path.join(
                media_dir, bias_csv_template.format(quarter=quarter_name)
            )
            media_bias_dict = {}
            if os.path.exists(media_file_path):
                print(f"  -> readmediaBias: {os.path.basename(media_file_path)}")
                df_media = pd.read_csv(media_file_path, encoding="utf-8-sig", dtype=str)
                media_bias_dict = _bias_lookup_dict_from_table(
                    df_media, ("user_id", "retweeted_user_id")
                )
                if not media_bias_dict:
                    print(f"  [error] media column: {list(df_media.columns)}")
            else:
                print(f"  [warning] mediafile: {media_file_path}")

            print("  -> processing Bias ...")
            if pol_bias_dict:
                df_node["politician_bias"] = df_node["user_id"].map(pol_bias_dict)
            if media_bias_dict:
                df_node["media_bias"] = df_node["user_id"].map(media_bias_dict)

            output_filename = f"{quarter_name}_top1pct_community_detection_results_with_bias.csv"
            output_path = os.path.join(current_node_dir, output_filename)
            df_node.to_csv(output_path, index=False, encoding="utf-8-sig")

            pol_count = int(df_node["politician_bias"].notna().sum())
            media_count = int(df_node["media_bias"].notna().sum())
            print(f"  -> save: {output_filename}")
            print(f"     politicianBias: {pol_count}")
            print(f"     mediaBias: {media_count}")
            if pol_count == 0 and media_count == 0:
                print(
                    f"  [warning] quarter bias :\n"
                    f"       {pol_file_path}\n"
                    f"       {media_file_path}"
                )

        except Exception as e:
            print(f"  [] process {quarter_name} error: {e}")
            traceback.print_exc()

    print("\nprocessdone ")


# =============================================================================
# =============================================================================
def classify_community_nodes_by_bias_top1_percent(
    periods=None,
    base_dir=TOP1_PCT_HUB_ROOT,
    input_csv_template="{quarter}_top1pct_community_detection_results_with_bias.csv",
    output_csv_template="{quarter}_top1pct_community_detection_results_classified.csv",
):
    """Project workflow helper."""

    def classify_politician(score):
        if pd.isna(score):
            return None
        try:
            s = float(score)
        except (TypeError, ValueError):
            return None
        th_n, th_p = -1 / 3, 1 / 3
        if -1 <= s < th_n:
            return "Left"
        if th_n <= s <= th_p:
            return "Center"
        if th_p < s <= 1:
            return "Right"
        return None

    def classify_media(score):
        """Project workflow helper."""
        if pd.isna(score):
            return None
        try:
            s = float(score)
        except (TypeError, ValueError):
            return None
        if -3 <= s < -2.5:
            return "Extreme bias Left"
        if -2.5 <= s < -1.5:
            return "Left"
        if -1.5 <= s < -0.5:
            return "Left leaning"
        if -0.5 <= s <= 0.5:
            return "Center"
        if 0.5 < s < 1.5:
            return "Right leaning"
        if 1.5 <= s < 2.5:
            return "Right"
        if 2.5 <= s <= 3:
            return "Extreme bias right"
        return None

    if periods is None:
        periods = _top1pct_default_quarters()

    for quarter_name in periods:
        print(f"\n{'='*40}")
        print(f"processingprocessclassify: {quarter_name}")

        current_dir = os.path.join(base_dir, quarter_name)
        input_filename = input_csv_template.format(quarter=quarter_name)
        input_path = os.path.join(current_dir, input_filename)

        if not os.path.exists(input_path):
            print(f"  [skip] inputfile: {input_path}")
            print("  row  Bias  ")
            continue

        try:
            print("  -> readfile...")
            df = pd.read_csv(input_path, encoding="utf-8-sig", dtype={"user_id": str})
            df.columns = df.columns.str.strip()

            if "politician_bias" not in df.columns or "media_bias" not in df.columns:
                raise ValueError(f"missing politician_bias/media_bias column : {list(df.columns)}")

            df["politician_bias"] = pd.to_numeric(df["politician_bias"], errors="coerce")
            df["media_bias"] = pd.to_numeric(df["media_bias"], errors="coerce")

            print("  -> processingclassify...")
            df["politician_bias_category"] = df["politician_bias"].apply(classify_politician)
            df["media_bias_category"] = df["media_bias"].apply(classify_media)

            print("     [summary]")
            print(f"     politician_category: {df['politician_bias_category'].value_counts(dropna=False).to_dict()}")
            print(f"     media_category: {df['media_bias_category'].value_counts(dropna=False).to_dict()}")

            output_filename = output_csv_template.format(quarter=quarter_name)
            output_path = os.path.join(current_dir, output_filename)
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
            print(f"  -> save: {output_filename}")

        except Exception as e:
            print(f"  [error] process: {e}")
            traceback.print_exc()

    print("\nquarterclassifyprocessdone ")


def _node_attr_value_for_gexf(val):
    """Project workflow helper."""
    if val is None:
        return None
    if isinstance(val, float) and np.isnan(val):
        return None
    if pd.isna(val):
        return None
    if isinstance(val, (np.floating, float)):
        return float(val)
    if isinstance(val, (np.integer, int)):
        return int(val)
    s = str(val).strip()
    return s if s and s.lower() != "nan" else None


# =============================================================================
# =============================================================================
def write_classified_node_attributes_to_gexf_top1_percent(
    periods=None,
    base_dir=TOP1_PCT_HUB_ROOT,
    gexf_params_tag="res1.0_seed42",
    gexf_filename_template="{quarter}_{params_tag}.gexf",
    output_suffix="_with_political_attributes",
    completed_csv_template="{quarter}_top1pct_community_detection_results_classified.csv",
    attr_columns=(
        "politician_bias",
        "media_bias",
        "politician_bias_category",
        "media_bias_category",
    ),
):
    """Project workflow helper."""
    if periods is None:
        periods = _top1pct_default_quarters()

    for quarter_name in periods:
        print(f"\n{'='*40}")
        print(f"GEXF write: {quarter_name}")

        current_dir = os.path.join(base_dir, quarter_name)
        gexf_in = os.path.join(
            current_dir,
            gexf_filename_template.format(quarter=quarter_name, params_tag=gexf_params_tag),
        )
        csv_path = os.path.join(
            current_dir,
            completed_csv_template.format(quarter=quarter_name),
        )
        base_name, ext = os.path.splitext(os.path.basename(gexf_in))
        if ext.lower() != ".gexf":
            base_name = os.path.basename(gexf_in)
            ext = ".gexf"
        gexf_out = os.path.join(current_dir, f"{base_name}{output_suffix}{ext}")

        if not os.path.exists(gexf_in):
            print(f"  [skip]  GEXF : {gexf_in}")
            continue
        if not os.path.exists(csv_path):
            print(f"  [skip] classified CSV : {csv_path}")
            print("  row  Bias  political_bias  ")
            continue

        try:
            G = nx.read_gexf(gexf_in)
            df = pd.read_csv(csv_path, encoding="utf-8-sig", dtype={"user_id": str})
            df.columns = df.columns.str.strip()

            if "user_id" not in df.columns:
                raise ValueError(f"CSV missing user_id column: {list(df.columns)}")

            missing_cols = [c for c in attr_columns if c not in df.columns]
            if missing_cols:
                raise ValueError(f"CSV missingcolumn: {missing_cols}")

            df["user_id"] = df["user_id"].astype(str).str.strip()
            df = df.drop_duplicates(subset=["user_id"], keep="first")
            lookup = df.set_index("user_id")

            n_matched = 0
            n_attrs_set = 0
            for node in G.nodes():
                uid = str(node).strip()
                if uid not in lookup.index:
                    continue
                row = lookup.loc[uid]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                n_matched += 1
                for col in attr_columns:
                    v = _node_attr_value_for_gexf(row[col])
                    if v is not None:
                        gexf_key = _CSV_ATTR_TO_GEXF.get(col, col)
                        G.nodes[node][gexf_key] = v
                        n_attrs_set += 1

            nx.write_gexf(G, gexf_out, encoding="utf-8")
            print(f"  -> write  CSV  : {n_matched}")
            print(f"  -> write  : {n_attrs_set}")
            print(f"  -> save: {gexf_out}")

        except Exception as e:
            print(f"  [error] {quarter_name}: {e}")
            traceback.print_exc()

    print("\n GEXF  done ")




import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

def rgb_to_hex(rgb_str):
    """Project workflow helper."""
    try:
        rgb_values = rgb_str.replace('rgb(', '').replace(')', '').split(',')
        return tuple(int(v.strip()) / 255.0 for v in rgb_values)
    except:
        return (0.5, 0.5, 0.5)

# =============================================================================
# =============================================================================
def analyze_community_political_distribution_Top1Percent(periods, base_root=TOP1_PCT_HUB_ROOT):
    COLOR_MAP_MEDIA = {
        'Extreme bias Left': rgb_to_hex('rgb(0, 51, 102)'),
        'Left': rgb_to_hex('rgb(51, 102, 153)'),
        'Left leaning': rgb_to_hex('rgb(181, 216, 243)'),
        'Center': rgb_to_hex('rgb(240, 230, 140)'),
        'Right leaning': rgb_to_hex('rgb(255, 153, 153)'),
        'Right': rgb_to_hex('rgb(204, 102, 102)'),
        'Extreme bias right': rgb_to_hex('rgb(139, 26, 26)'),
        'DEFAULT': rgb_to_hex('rgb(128, 128, 128)')
    }
    
    COLOR_MAP_POLITICIAN = {
        'Left': rgb_to_hex('rgb(51, 102, 153)'),
        'Center': rgb_to_hex('rgb(240, 230, 140)'),
        'Right': rgb_to_hex('rgb(204, 102, 102)'),
        'DEFAULT': rgb_to_hex('rgb(128, 128, 128)')
    }

    COLOR_MAP_MEDIA_LOWER = {k.lower(): v for k, v in COLOR_MAP_MEDIA.items()}

    top_n = 3
    n_bins_pol, pol_range = 20, (-1, 1)
    n_bins_med, med_range = 30, (-3, 3)
    edges_pol = np.linspace(pol_range[0], pol_range[1], n_bins_pol + 1)
    edges_med = np.linspace(med_range[0], med_range[1], n_bins_med + 1)

    period_data = []  # (period, period_folder, df, top_comm_ids)
    max_pol_y = 0.0
    max_med_y = 0.0

    for period in periods:
        print(f"\n>>> processingprocessquarter: {period}")
        period_folder = os.path.join(base_root, period)
        input_csv_path = os.path.join(period_folder, f"{period}_top1pct_community_detection_results_classified.csv")

        if not os.path.exists(input_csv_path):
            print(f"file: {input_csv_path}")
            continue

        df = pd.read_csv(input_csv_path, encoding='utf-8-sig')

        df['politician_bias_category'] = df['politician_bias_category'].astype(str).str.strip()
        df['media_category_match'] = df['media_bias_category'].astype(str).str.strip().str.lower()

        top_comm_ids = df['community_id'].value_counts().head(top_n).index.tolist()
        period_data.append((period, period_folder, df, top_comm_ids))

        for cid in top_comm_ids:
            sub_pol = df[(df['community_id'] == cid) & (df['politician_bias'].notna())]
            total_pol = np.zeros(n_bins_pol, dtype=float)
            for label, color in COLOR_MAP_POLITICIAN.items():
                if label == 'DEFAULT':
                    continue
                cat_data = sub_pol[sub_pol['politician_bias_category'] == label]['politician_bias']
                if cat_data.empty:
                    continue
                c, _ = np.histogram(cat_data, bins=edges_pol)
                total_pol += c
            max_pol_y = max(max_pol_y, float(total_pol.max()) if len(total_pol) else 0.0)

            sub_med = df[(df['community_id'] == cid) & (df['media_bias'].notna())]
            total_med = np.zeros(n_bins_med, dtype=float)
            for label_name, color in COLOR_MAP_MEDIA.items():
                if label_name == 'DEFAULT':
                    continue
                label_lower = label_name.lower()
                cat_data = sub_med[sub_med['media_category_match'] == label_lower]['media_bias']
                if cat_data.empty:
                    continue
                c, _ = np.histogram(cat_data, bins=edges_med)
                total_med += c
            max_med_y = max(max_med_y, float(total_med.max()) if len(total_med) else 0.0)

    y_lim_pol = max(max_pol_y * 1.05, 1.0)
    y_lim_med = max(max_med_y * 1.05, 1.0)
    print(f"\n[ Y ] politician ylim : {y_lim_pol:.1f} media ylim : {y_lim_med:.1f}")

    for period, period_folder, df, top_comm_ids in period_data:
        fig1, axes1 = plt.subplots(1, top_n, figsize=(18, 5))
        fig1.suptitle(f'{period} - Politician Bias Distribution (Top 3 Communities)', fontsize=16, fontweight='bold')

        for i, cid in enumerate(top_comm_ids):
            ax = axes1[i]
            sub_df = df[(df['community_id'] == cid) & (df['politician_bias'].notna())]

            for label, color in COLOR_MAP_POLITICIAN.items():
                if label == 'DEFAULT':
                    continue
                cat_data = sub_df[sub_df['politician_bias_category'] == label]['politician_bias']
                if not cat_data.empty:
                    ax.hist(cat_data, bins=edges_pol, color=color, alpha=0.7, label=label)

            ax.set_title(f'Comm ID: {cid}\nNodes: {len(df[df["community_id"]==cid])}')
            ax.set_xlim(-1, 1)
            ax.set_ylim(0, y_lim_pol)
            ax.set_xlabel('Politician Bias')
            if i == 0:
                ax.set_ylabel('User Count')

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(os.path.join(period_folder, f"{period}_Politician_Bias_Top3.png"), dpi=300)
        plt.close()

        fig2, axes2 = plt.subplots(1, top_n, figsize=(18, 5))
        fig2.suptitle(f'{period} - Media Bias Distribution (Top 3 Communities)', fontsize=16, fontweight='bold')

        for i, cid in enumerate(top_comm_ids):
            ax = axes2[i]
            sub_df = df[(df['community_id'] == cid) & (df['media_bias'].notna())]

            for label_name, color in COLOR_MAP_MEDIA.items():
                if label_name == 'DEFAULT':
                    continue
                label_lower = label_name.lower()
                cat_data = sub_df[sub_df['media_category_match'] == label_lower]['media_bias']

                if not cat_data.empty:
                    ax.hist(cat_data, bins=edges_med, color=color, alpha=0.7, label=label_name)

            ax.set_title(f'Comm ID: {cid}\nNodes: {len(df[df["community_id"]==cid])}')
            ax.set_xlim(-3, 3)
            ax.set_ylim(0, y_lim_med)
            ax.set_xlabel('Media Bias')
            if i == 0:
                ax.set_ylabel('User Count')

        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(os.path.join(period_folder, f"{period}_Media_Bias_Top3.png"), dpi=300)
        plt.close()

        print(f"   -> {period} done ")

    print("\n[done] generate ")



import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

def plot_merged_bias_distribution_Top1Percent(periods, base_root=TOP1_PCT_HUB_ROOT):
    def rgb_to_hex(rgb_str):
        try:
            rgb_values = rgb_str.replace('rgb(', '').replace(')', '').split(',')
            return tuple(int(v.strip()) / 255.0 for v in rgb_values)
        except: return (0.5, 0.5, 0.5)

    COLOR_MAP_MEDIA = {
        'Extreme bias Left': rgb_to_hex('rgb(0, 51, 102)'),
        'Left': rgb_to_hex('rgb(51, 102, 153)'),
        'Left leaning': rgb_to_hex('rgb(181, 216, 243)'),
        'Center': rgb_to_hex('rgb(240, 230, 140)'),
        'Right leaning': rgb_to_hex('rgb(255, 153, 153)'),
        'Right': rgb_to_hex('rgb(204, 102, 102)'),
        'Extreme bias right': rgb_to_hex('rgb(139, 26, 26)')
    }
    COLOR_MAP_POLITICIAN = {
        'Left': rgb_to_hex('rgb(51, 102, 153)'),
        'Center': rgb_to_hex('rgb(240, 230, 140)'),
        'Right': rgb_to_hex('rgb(204, 102, 102)')
    }

    merged_data = {0: [], 1: [], 2: []}
    periods_loaded = []
    for period in periods:
        input_csv_path = os.path.join(base_root, period, f"{period}_top1pct_community_detection_results_classified.csv")
        if not os.path.exists(input_csv_path):
            continue
        df = pd.read_csv(input_csv_path, encoding='utf-8-sig')
        df['politician_category'] = df['politician_bias_category'].astype(str).str.strip()
        df['media_category'] = df['media_bias_category'].astype(str).str.strip().str.lower()
        df.loc[df['media_category'].isin(['nan', 'none', 'nat', '']), 'media_category'] = np.nan
        top_comm_ids = df['community_id'].value_counts().head(3).index.tolist()
        for rank, cid in enumerate(top_comm_ids):
            sub_df = df[df['community_id'] == cid].copy()
            merged_data[rank].append(sub_df)
        periods_loaded.append(period)

    diag_parts = [pd.concat(merged_data[r], ignore_index=True) for r in range(3) if merged_data[r]]
    if not diag_parts:
        q0 = periods[0] if periods else "quarter"
        print(
            "[ Merged Top1%] mergedata  base_root eachquarter "
            f"{q0}_top1pct_community_detection_results_classified.csv file "
        )
    else:
        diag_df = pd.concat(diag_parts, ignore_index=True)
        pol_n = int(diag_df["politician_bias"].notna().sum()) if "politician_bias" in diag_df.columns else 0
        med_n = int(diag_df["media_bias"].notna().sum()) if "media_bias" in diag_df.columns else 0
        print(
            f"[ Merged Top1%] quarter={len(periods_loaded)}/{len(periods)}, "
            f"mergerow={len(diag_df)}, politician_bias={pol_n}, media_bias={med_n}"
        )
        if "politician_bias_category" in diag_df.columns:
            pol_vc = diag_df["politician_bias_category"].dropna().astype(str).str.strip().value_counts().head(8)
            print(f"[ Merged Top1%] politician_bias_category() Top: {pol_vc.to_dict()}")
        if "media_bias_category" in diag_df.columns:
            med_vc = (
                diag_df["media_bias_category"].dropna().astype(str).str.strip().str.lower().value_counts().head(12)
            )
            print(f"[ Merged Top1%] media_bias_category() Top: {med_vc.to_dict()}")
        expected_med = {k.lower() for k in COLOR_MAP_MEDIA}
        if med_n > 0 and "media_bias_category" in diag_df.columns:
            raw_lower = diag_df["media_bias_category"].dropna().astype(str).str.strip().str.lower()
            unmatched = raw_lower[~raw_lower.isin(expected_med) & ~raw_lower.isin(["nan", "none", "nat", ""])]
            if len(unmatched):
                um = unmatched.value_counts().head(8)
                print(
                    "[ Merged Top1%] media_category COLOR_MAP 7   : "
                    f"{um.to_dict()}     CSV  Extreme bias Left / Left /    "
                )

    n_bins_pol, pol_range = 20, (-1, 1)
    n_bins_med, med_range = 30, (-3, 3)
    edges_pol = np.linspace(pol_range[0], pol_range[1], n_bins_pol + 1)
    edges_med = np.linspace(med_range[0], med_range[1], n_bins_med + 1)

    max_pol_y = 0.0
    max_med_y = 0.0
    for rank in range(3):
        all_rank_df = pd.concat(merged_data[rank]) if merged_data[rank] else pd.DataFrame()
        if all_rank_df.empty:
            continue
        pol_df = all_rank_df[all_rank_df['politician_bias'].notna()]
        total_pol = np.zeros(n_bins_pol, dtype=float)
        for label, color in COLOR_MAP_POLITICIAN.items():
            cat_data = pol_df[pol_df['politician_category'].str.lower() == label.lower()]['politician_bias']
            if cat_data.empty:
                continue
            c, _ = np.histogram(cat_data, bins=edges_pol)
            total_pol += c
        max_pol_y = max(max_pol_y, float(total_pol.max()) if len(total_pol) else 0.0)

        med_df = all_rank_df[all_rank_df['media_bias'].notna()]
        total_med = np.zeros(n_bins_med, dtype=float)
        for label_orig, color in COLOR_MAP_MEDIA.items():
            label_lower = label_orig.lower()
            cat_data = med_df[med_df['media_category'] == label_lower]['media_bias']
            if cat_data.empty:
                continue
            c, _ = np.histogram(cat_data, bins=edges_med)
            total_med += c
        max_med_y = max(max_med_y, float(total_med.max()) if len(total_med) else 0.0)

    y_lim_pol = max(max_pol_y * 1.05, 1.0)
    y_lim_med = max(max_med_y * 1.05, 1.0)
    print(f"\n[ Y ] politician ylim : {y_lim_pol:.1f} media ylim : {y_lim_med:.1f}")

    fig, axes = plt.subplots(2, 3, figsize=(20, 12), dpi=150) 
    
    fig.suptitle('Merged Political Bias Distribution (6 Quarters Aggregated)', 
                 fontsize=24, fontweight='bold', y=0.96)

    col_titles = ['Top 1 Community', 'Top 2 Community', 'Top 3 Community']

    for rank in range(3):
        all_rank_df = pd.concat(merged_data[rank]) if merged_data[rank] else pd.DataFrame()
        ax_pol = axes[0, rank]
        ax_med = axes[1, rank]
        ax_pol.set_title(col_titles[rank], fontsize=18, fontweight='bold', pad=20)
        ax_pol.set_xlim(-1, 1)
        ax_pol.set_ylim(0, y_lim_pol)
        ax_med.set_xlim(-3, 3)
        ax_med.set_ylim(0, y_lim_med)
        if all_rank_df.empty:
            continue

        pol_df = all_rank_df[all_rank_df['politician_bias'].notna()]
        for label, color in COLOR_MAP_POLITICIAN.items():
            cat_data = pol_df[pol_df['politician_category'].str.lower() == label.lower()]['politician_bias']
            if not cat_data.empty:
                ax_pol.hist(cat_data, bins=edges_pol, color=color, alpha=0.7, label=label)
        
        if rank == 0: 
            ax_pol.set_ylabel('Politicians\n\nUser Count', fontsize=16, fontweight='bold')
        ax_pol.grid(axis='y', linestyle='--', alpha=0.3)

        med_df = all_rank_df[all_rank_df['media_bias'].notna()]
        for label_orig, color in COLOR_MAP_MEDIA.items():
            label_lower = label_orig.lower()
            cat_data = med_df[med_df['media_category'] == label_lower]['media_bias']
            if not cat_data.empty:
                ax_med.hist(cat_data, bins=edges_med, color=color, alpha=0.7, label=label_orig)
        
        ax_med.set_xlabel('Bias Score', fontsize=14)
        if rank == 0: 
            ax_med.set_ylabel('Media\n\nUser Count', fontsize=16, fontweight='bold')
        ax_med.grid(axis='y', linestyle='--', alpha=0.3)

    # axes[0, 2].legend(title="Politician Category", loc='upper right', fontsize=10, frameon=True)
    # axes[1, 2].legend(title="Media Category", loc='upper right', fontsize=10, frameon=True)

    plt.subplots_adjust(top=0.88, bottom=0.08, left=0.1, right=0.95, hspace=0.3, wspace=0.25)
    
    save_path = os.path.join(base_root, "Merged_Political_Media_Bias_Distribution_Clean.png")
    plt.savefig(save_path, bbox_inches='tight')
    print(f"mergegenerate {save_path}")
    plt.show()


# =============================================================================
# =============================================================================
def plot_quarterly_media_bias_distribution_top1_top2_Top1Percent(
    periods,
    base_root=TOP1_PCT_HUB_ROOT
):
    """Project workflow helper."""
    def rgb_to_hex(rgb_str):
        try:
            rgb_values = rgb_str.replace('rgb(', '').replace(')', '').split(',')
            return tuple(int(v.strip()) / 255.0 for v in rgb_values)
        except:
            return (0.5, 0.5, 0.5)

    COLOR_MAP_MEDIA = {
        'Extreme bias Left': rgb_to_hex('rgb(0, 51, 102)'),
        'Left': rgb_to_hex('rgb(51, 102, 153)'),
        'Left leaning': rgb_to_hex('rgb(181, 216, 243)'),
        'Center': rgb_to_hex('rgb(240, 230, 140)'),
        'Right leaning': rgb_to_hex('rgb(255, 153, 153)'),
        'Right': rgb_to_hex('rgb(204, 102, 102)'),
        'Extreme bias right': rgb_to_hex('rgb(139, 26, 26)')
    }

    n_bins_med, med_range = 30, (-3, 3)
    edges_med = np.linspace(med_range[0], med_range[1], n_bins_med + 1)

    global_max_med_y = 0.0
    periods_loaded = 0
    for period in periods:
        input_csv_path = os.path.join(base_root, period, f"{period}_top1pct_community_detection_results_classified.csv")
        if not os.path.exists(input_csv_path):
            continue
        df = pd.read_csv(input_csv_path, encoding='utf-8-sig')
        if df.empty:
            continue

        df['media_category'] = df['media_bias_category'].astype(str).str.strip().str.lower()
        df.loc[df['media_category'].isin(['nan', 'none', 'nat', '']), 'media_category'] = np.nan

        top_comm_ids = df['community_id'].value_counts().head(2).index.tolist()
        if len(top_comm_ids) < 2:
            continue

        cid_top1, cid_top2 = top_comm_ids[0], top_comm_ids[1]
        for cid in (cid_top1, cid_top2):
            sub_df = df[df['community_id'] == cid]
            med_df = sub_df[sub_df['media_bias'].notna()]
            total_med = np.zeros(n_bins_med, dtype=float)
            for label_orig in COLOR_MAP_MEDIA.keys():
                label_lower = label_orig.lower()
                cat_data = med_df[med_df['media_category'] == label_lower]['media_bias']
                if cat_data.empty:
                    continue
                c, _ = np.histogram(cat_data, bins=edges_med)
                total_med += c
            global_max_med_y = max(global_max_med_y, float(total_med.max()) if len(total_med) else 0.0)
        periods_loaded += 1

    y_lim_med_global = max(global_max_med_y * 1.05, 1.0)
    print(f"\n[ Y ] media ylim (quarter Top1/Top2): {y_lim_med_global:.1f} quarter={periods_loaded}/{len(periods)} ")

    for period in periods:
        input_csv_path = os.path.join(base_root, period, f"{period}_top1pct_community_detection_results_classified.csv")
        if not os.path.exists(input_csv_path):
            print(f"[skip] file: {input_csv_path}")
            continue

        df = pd.read_csv(input_csv_path, encoding='utf-8-sig')
        if df.empty:
            print(f"[skip] file: {input_csv_path}")
            continue

        df['media_category'] = df['media_bias_category'].astype(str).str.strip().str.lower()
        df.loc[df['media_category'].isin(['nan', 'none', 'nat', '']), 'media_category'] = np.nan

        top_comm_ids = df['community_id'].value_counts().head(2).index.tolist()
        if len(top_comm_ids) < 2:
            print(f"[skip] {period} generate Top1+Top2   {len(top_comm_ids)}  ")
            continue

        cid_top1, cid_top2 = top_comm_ids[0], top_comm_ids[1]
        sub_top1 = df[df['community_id'] == cid_top1].copy()
        sub_top2 = df[df['community_id'] == cid_top2].copy()

        fig, ax = plt.subplots(1, 1, figsize=(10, 10), dpi=150)
        ax.set_title(
            f"Media Bias Distribution (Top1 overlaid on Top2)\n{period}",
            fontsize=18,
            fontweight='bold',
            pad=14,
        )
        ax.set_xlim(med_range[0], med_range[1])
        ax.set_ylim(0, y_lim_med_global)

        def _plot_one(ax_, sub_df, *, hatch=None, alpha=0.7):
            med_df = sub_df[sub_df['media_bias'].notna()]
            for label_orig, color in COLOR_MAP_MEDIA.items():
                label_lower = label_orig.lower()
                cat_data = med_df[med_df['media_category'] == label_lower]['media_bias']
                if cat_data.empty:
                    continue
                ax_.hist(
                    cat_data,
                    bins=edges_med,
                    color=color,
                    alpha=alpha,
                    hatch=hatch,
                    edgecolor='black' if hatch else None,
                    linewidth=0.25 if hatch else 0,
                )

        _plot_one(ax, sub_top2, hatch=None, alpha=0.55)
        _plot_one(ax, sub_top1, hatch='///', alpha=0.55)

        ax.set_xlabel('Bias Score', fontsize=13)
        ax.set_ylabel('Media\n\nUser Count', fontsize=15, fontweight='bold')
        ax.grid(axis='y', linestyle='--', alpha=0.3)

        plt.subplots_adjust(top=0.88, bottom=0.10, left=0.10, right=0.98)

        save_path = os.path.join(base_root, period, f"{period}_Top1Top2_Media_Bias_Distribution_Clean.png")
        plt.savefig(save_path, bbox_inches='tight')
        print(f"quarter Top1+Top2 mediagenerate {save_path}")
        plt.show()

def plot_quarterly_media_bias_distribution_without_axes_top1_percent(
    periods,
    base_root=TOP1_PCT_HUB_ROOT
):
    """Project workflow helper."""
    def rgb_to_hex(rgb_str):
        try:
            rgb_values = rgb_str.replace('rgb(', '').replace(')', '').split(',')
            return tuple(int(v.strip()) / 255.0 for v in rgb_values)
        except:
            return (0.5, 0.5, 0.5)

    COLOR_MAP_MEDIA = {
        'Extreme bias Left': rgb_to_hex('rgb(0, 51, 102)'),
        'Left': rgb_to_hex('rgb(51, 102, 153)'),
        'Left leaning': rgb_to_hex('rgb(181, 216, 243)'),
        'Center': rgb_to_hex('rgb(240, 230, 140)'),
        'Right leaning': rgb_to_hex('rgb(255, 153, 153)'),
        'Right': rgb_to_hex('rgb(204, 102, 102)'),
        'Extreme bias right': rgb_to_hex('rgb(139, 26, 26)')
    }

    n_bins_med, med_range = 30, (-3, 3)
    edges_med = np.linspace(med_range[0], med_range[1], n_bins_med + 1)

    global_max_med_y = 0.0
    periods_loaded = 0
    for period in periods:
        input_csv_path = os.path.join(base_root, period, f"{period}_top1pct_community_detection_results_classified.csv")
        if not os.path.exists(input_csv_path):
            continue
        df = pd.read_csv(input_csv_path, encoding='utf-8-sig')
        if df.empty:
            continue

        df['media_category'] = df['media_bias_category'].astype(str).str.strip().str.lower()
        df.loc[df['media_category'].isin(['nan', 'none', 'nat', '']), 'media_category'] = np.nan

        top_comm_ids = df['community_id'].value_counts().head(2).index.tolist()
        if len(top_comm_ids) < 2:
            continue

        cid_top1, cid_top2 = top_comm_ids[0], top_comm_ids[1]
        for cid in (cid_top1, cid_top2):
            sub_df = df[df['community_id'] == cid]
            med_df = sub_df[sub_df['media_bias'].notna()]
            total_med = np.zeros(n_bins_med, dtype=float)
            for label_orig in COLOR_MAP_MEDIA.keys():
                label_lower = label_orig.lower()
                cat_data = med_df[med_df['media_category'] == label_lower]['media_bias']
                if cat_data.empty:
                    continue
                c, _ = np.histogram(cat_data, bins=edges_med)
                total_med += c
            global_max_med_y = max(global_max_med_y, float(total_med.max()) if len(total_med) else 0.0)
        periods_loaded += 1

    y_lim_med_global = max(global_max_med_y * 1.05, 1.0)
    print(f"\n[ Y ]  media ylim (quarter Top1/Top2): {y_lim_med_global:.1f} quarter={periods_loaded}/{len(periods)} ")

    for period in periods:
        input_csv_path = os.path.join(base_root, period, f"{period}_top1pct_community_detection_results_classified.csv")
        if not os.path.exists(input_csv_path):
            print(f"[skip] file: {input_csv_path}")
            continue

        df = pd.read_csv(input_csv_path, encoding='utf-8-sig')
        if df.empty:
            print(f"[skip] file: {input_csv_path}")
            continue

        df['media_category'] = df['media_bias_category'].astype(str).str.strip().str.lower()
        df.loc[df['media_category'].isin(['nan', 'none', 'nat', '']), 'media_category'] = np.nan

        top_comm_ids = df['community_id'].value_counts().head(2).index.tolist()
        if len(top_comm_ids) < 2:
            print(f"[skip] {period} generate Top1+Top2   {len(top_comm_ids)}  ")
            continue

        cid_top1, cid_top2 = top_comm_ids[0], top_comm_ids[1]
        sub_top1 = df[df['community_id'] == cid_top1].copy()
        sub_top2 = df[df['community_id'] == cid_top2].copy()

        fig, ax = plt.subplots(1, 1, figsize=(10, 10), dpi=150)
        ax.set_xlim(med_range[0], med_range[1])
        ax.set_ylim(0, y_lim_med_global)

        def _plot_one(ax_, sub_df, *, hatch=None, alpha=0.7):
            med_df = sub_df[sub_df['media_bias'].notna()]
            for label_orig, color in COLOR_MAP_MEDIA.items():
                label_lower = label_orig.lower()
                cat_data = med_df[med_df['media_category'] == label_lower]['media_bias']
                if cat_data.empty:
                    continue
                ax_.hist(
                    cat_data,
                    bins=edges_med,
                    color=color,
                    alpha=alpha,
                    hatch=hatch,
                    edgecolor='black' if hatch else None,
                    linewidth=0.25 if hatch else 0,
                )

        _plot_one(ax, sub_top2, hatch=None, alpha=0.55)
        _plot_one(ax, sub_top1, hatch='///', alpha=0.55)

        ax.grid(axis='y', linestyle='--', alpha=0.3)

        ax.tick_params(axis='both', which='both', labelbottom=False, labelleft=False)
        ax.tick_params(axis='both', which='both', length=6, width=1)

        plt.subplots_adjust(top=0.88, bottom=0.10, left=0.10, right=0.98)

        save_path = os.path.join(base_root, period, f"{period}_Top1Top2_Media_Bias_Distribution_.png")
        plt.savefig(save_path, bbox_inches='tight')
        print(f"quarter Top1+Top2 mediagenerate {save_path}")
        plt.show()





# =============================================================================
# =============================================================================
def extract_top3_community_core_nodes_by_quarter_Top1Percent(
    periods,
    base_root=TOP1_PCT_HUB_ROOT,
    resolution=1.0,
    random_seed=42,
    ranking_type='weighted_degree',
    top_k_core=1,
    save_per_period=True,
):
    """Project workflow helper."""
    if ranking_type not in ('weighted_degree', 'pagerank'):
        raise ValueError("ranking_type  'weighted_degree'  'pagerank'")
    if not isinstance(top_k_core, int) or top_k_core <= 0:
        raise ValueError("top_k_core ")

    params_tag = f"res{resolution}_seed{random_seed}"
    score_col = 'weighted_degree' if ranking_type == 'weighted_degree' else 'pagerank'

    all_rows = []

    for period in periods:
        period_folder = os.path.join(base_root, period)
        metrics_path = os.path.join(period_folder, f"{period}_{params_tag}_top3_community_metrics.csv")
        top10_path = os.path.join(period_folder, f"{period}_{params_tag}_top10_nodes.csv")

        if not os.path.exists(metrics_path):
            print(f"[skip] file: {metrics_path}")
            continue
        if not os.path.exists(top10_path):
            print(f"[skip] Top10file: {top10_path}")
            continue

        df_metrics = pd.read_csv(metrics_path, encoding='utf-8-sig')
        df_top10 = pd.read_csv(top10_path, encoding='utf-8-sig')

        if not {'rank', 'community_id'}.issubset(df_metrics.columns):
            raise ValueError(f"{metrics_path} missing rank/community_id")
        if not {'user_id', 'louvain_community', 'ranking_type'}.issubset(df_top10.columns):
            raise ValueError(f"{top10_path} missing user_id/louvain_community/ranking_type")

        df_metrics = df_metrics.sort_values('rank').head(3).copy()

        df_top10_rt = df_top10[df_top10['ranking_type'] == ranking_type].copy()
        if score_col not in df_top10_rt.columns:
            df_top10_rt[score_col] = np.nan

        for _, mrow in df_metrics.iterrows():
            comm_rank = int(mrow['rank'])
            comm_id = mrow['community_id']

            comm_nodes = df_top10_rt[df_top10_rt['louvain_community'] == comm_id].copy()
            if comm_nodes.empty:
                comm_nodes = df_top10_rt[df_top10_rt['louvain_community'].astype(str) == str(comm_id)].copy()

            if comm_nodes.empty:
                print(f"[warning] {period} Top{comm_rank} (comm_id={comm_id})  Top10 file ranking_type={ranking_type}  ")
                continue

            comm_nodes = comm_nodes.sort_values(score_col, ascending=False)
            core_nodes = comm_nodes.head(top_k_core)

            for core_rank, (_, nrow) in enumerate(core_nodes.iterrows(), 1):
                all_rows.append({
                    'period': period,
                    'community_rank': comm_rank,
                    'community_id': comm_id,
                    'core_rank': core_rank,
                    'user_id': str(nrow['user_id']),
                    'ranking_type': ranking_type,
                    'score': nrow.get(score_col, np.nan),
                })

        if save_per_period:
            out_df = pd.DataFrame([r for r in all_rows if r['period'] == period])
            out_path = os.path.join(
                period_folder,
                f"{period}_{params_tag}_top3_community_core_nodes_{ranking_type}_top{top_k_core}.csv"
            )
            out_df.to_csv(out_path, index=False, encoding='utf-8-sig')
            print(f"[save] {period} Top3 : {out_path}")

    return pd.DataFrame(all_rows)





















# ============================================================
# ============================================================



# =============================================================================
# =============================================================================
def extract_top3_communities_hub_keywords_tfidf_by_quarter_Top1Percent(
    periods,
    base_root=TOP1_PCT_HUB_ROOT,
    resolution=1.0,
    random_seed=42,
    ranking_type_for_hub='weighted_degree',
    hub_top_n=10,
    keyword_base_dir=KEYWORD_COV_DIR,
    stop_words='english',
    top_n_keywords=30,
    save_scores_csv=True,
    save_top_keywords_csv=True,
    use_tqdm=True,
):
    """Project workflow helper."""
    import re
    from sklearn.feature_extraction.text import TfidfVectorizer
    try:
        from tqdm import tqdm  # type: ignore
    except Exception:
        tqdm = None

    if ranking_type_for_hub not in ('weighted_degree', 'pagerank'):
        raise ValueError("ranking_type_for_hub  'weighted_degree'  'pagerank'")
    if not isinstance(hub_top_n, int) or hub_top_n <= 0:
        raise ValueError("hub_top_n ")
    if not isinstance(top_n_keywords, int) or top_n_keywords <= 0:
        raise ValueError("top_n_keywords ")

    params_tag = f"res{resolution}_seed{random_seed}"

    def _period_to_months(period_str: str):
        parts = period_str.split('_')
        if len(parts) % 2 != 0:
            raise ValueError(f" period month: {period_str}")
        months = []
        for i in range(0, len(parts), 2):
            months.append(f"{parts[i]}_{parts[i+1]}")
        return months

    def _split_keywords(matched_keywords):
        if matched_keywords is None or (isinstance(matched_keywords, float) and np.isnan(matched_keywords)):
            return []
        s = str(matched_keywords).strip().strip('"')
        toks = re.split(r'[,\s]+', s)
        return [t for t in toks if t]

    all_top_keywords_rows = []

    period_iter = periods
    if use_tqdm and tqdm is not None:
        period_iter = tqdm(periods, desc='TF-IDF by quarter', unit='quarter')

    for period in period_iter:
        period_folder = os.path.join(base_root, period)
        metrics_path = os.path.join(period_folder, f"{period}_{params_tag}_top3_community_metrics.csv")
        top10_path = os.path.join(period_folder, f"{period}_{params_tag}_top10_nodes.csv")

        if not os.path.exists(metrics_path):
            print(f"[skip] file: {metrics_path}")
            continue
        if not os.path.exists(top10_path):
            print(f"[skip] Top10file: {top10_path}")
            continue

        df_metrics = pd.read_csv(metrics_path, encoding='utf-8-sig').sort_values('rank').head(3)
        df_top10 = pd.read_csv(top10_path, encoding='utf-8-sig')

        top3 = [(int(r), cid) for r, cid in zip(df_metrics['rank'].tolist(), df_metrics['community_id'].tolist())]

        df_hub = df_top10[df_top10['ranking_type'] == ranking_type_for_hub].copy()
        hub_score_col = 'weighted_degree' if ranking_type_for_hub == 'weighted_degree' else 'pagerank'
        if hub_score_col not in df_hub.columns:
            df_hub[hub_score_col] = np.nan

        hub_nodes_by_comm = {}
        comm_col_name_map = {}
        for comm_rank, comm_id in top3:
            comm_df = df_hub[df_hub['louvain_community'].astype(str) == str(comm_id)].copy()
            comm_df = comm_df.sort_values(hub_score_col, ascending=False)
            hub_nodes_by_comm[(comm_rank, comm_id)] = set(comm_df['user_id'].astype(str).head(hub_top_n).tolist())
            comm_col_name_map[(comm_rank, comm_id)] = f"Top{comm_rank}_comm{comm_id}"

        months = _period_to_months(period)
        keyword_paths = [os.path.join(keyword_base_dir, f"matched_retweets_with_keywords_{ym}.csv") for ym in months]

        docs_by_comm = {k: [] for k in hub_nodes_by_comm.keys()}

        keyword_iter = keyword_paths
        if use_tqdm and tqdm is not None:
            keyword_iter = tqdm(keyword_paths, desc=f'{period} keyword files', unit='file', leave=False)

        for kp in keyword_iter:
            if not os.path.exists(kp):
                print(f"[note] file skip: {kp}")
                continue
            df_kw = pd.read_csv(kp, encoding='utf-8', dtype={'retweet_origin_user_id': str})
            if 'retweet_origin_user_id' not in df_kw.columns or 'matched_keywords' not in df_kw.columns:
                raise ValueError(f"{kp} missing retweet_origin_user_id  matched_keywords ")

            row_iter = df_kw.iterrows()
            if use_tqdm and tqdm is not None:
                row_iter = tqdm(row_iter, total=len(df_kw), desc=os.path.basename(kp), unit='row', leave=False)

            for _, row in row_iter:
                origin_id = str(row['retweet_origin_user_id'])
                kw_tokens = _split_keywords(row.get('matched_keywords', ''))
                if not kw_tokens:
                    continue
                doc_piece = ' '.join(kw_tokens)

                for comm_key, hub_set in hub_nodes_by_comm.items():
                    if origin_id in hub_set:
                        docs_by_comm[comm_key].append(doc_piece)

        comm_keys_in_order = list(hub_nodes_by_comm.keys())
        documents = [' '.join(docs_by_comm[k]).strip() for k in comm_keys_in_order]

        if all(d == '' for d in documents):
            print(f"[warning] {period}  Top3  Hub  ")
            continue

        vectorizer = TfidfVectorizer(stop_words=stop_words, lowercase=True)
        tfidf_matrix = vectorizer.fit_transform(documents)
        feature_names = vectorizer.get_feature_names_out()
        tfidf_scores = tfidf_matrix.toarray()

        if save_scores_csv:
            score_table = {'keyword': feature_names}
            for i, comm_key in enumerate(comm_keys_in_order):
                score_table[comm_col_name_map[comm_key]] = tfidf_scores[i]
            df_scores = pd.DataFrame(score_table)
            out_scores_path = os.path.join(period_folder, f"{period}_{params_tag}_Top3Community_Hub_TFIDF_keyword_scores.csv")
            df_scores.to_csv(out_scores_path, index=False, encoding='utf-8-sig')
            print(f"[save] {period} TF-IDF : {out_scores_path}")

        if save_top_keywords_csv:
            for i, comm_key in enumerate(comm_keys_in_order):
                comm_rank, comm_id = comm_key
                scores_vec = tfidf_scores[i]
                order = np.argsort(-scores_vec)
                top_idx = order[:top_n_keywords]
                for rank_i, idx in enumerate(top_idx, 1):
                    all_top_keywords_rows.append({
                        'period': period,
                        'community_rank': comm_rank,
                        'community_id': comm_id,
                        'keyword_rank': rank_i,
                        'keyword': feature_names[idx],
                        'tfidf_score': scores_vec[idx],
                        'hub_ranking_type': ranking_type_for_hub,
                        'hub_top_n': hub_top_n,
                    })

            out_top_path = os.path.join(period_folder, f"{period}_{params_tag}_Top{top_n_keywords}_TFIDF_keywords_long.csv")
            pd.DataFrame([r for r in all_top_keywords_rows if r['period'] == period]).to_csv(
                out_top_path, index=False, encoding='utf-8-sig'
            )
            print(f"[save] {period} Top{top_n_keywords}   : {out_top_path}")

    return pd.DataFrame(all_top_keywords_rows)










# =============================================================================
# =============================================================================
def append_top1_top2_mean_media_bias_to_top3_metrics_csv_Top1Percent(
    periods,
    base_root=TOP1_PCT_HUB_ROOT,
    gexf_params_tag="res1.0_seed42",
    metrics_params_tag="res1.0_seed42",
    out_col_name="mean_media_bias",
):
    """Project workflow helper."""
    for period in periods:
        period_folder = os.path.join(base_root, period)

        gexf_path = os.path.join(
            period_folder,
            f"{period}_{gexf_params_tag}_with_political_attributes.gexf",
        )
        metrics_csv_path = os.path.join(
            period_folder,
            f"{period}_{metrics_params_tag}_top3_community_metrics.csv",
        )

        if not os.path.exists(metrics_csv_path):
            print(f"[skip] file: {metrics_csv_path}")
            continue
        metrics_df = pd.read_csv(metrics_csv_path, encoding="utf-8-sig")
        if metrics_df.empty or "rank" not in metrics_df.columns or "community_id" not in metrics_df.columns:
            print(f"[skip] missingcolumn rank/community_id : {metrics_csv_path}")
            continue

        nodes_df = _load_nodes_community_media_bias(
            period_folder, gexf_params_tag=gexf_params_tag
        )
        if nodes_df is None:
            print(
                f"[skip] {period}  media_bias "
                f"  Step2 quarterfile quarterly_user_bias_scores_{period}.csv   "
            )
            if out_col_name not in metrics_df.columns:
                metrics_df[out_col_name] = np.nan
            metrics_df.to_csv(metrics_csv_path, index=False, encoding="utf-8-sig")
            continue

        try:
            gexf_top2 = (
                nodes_df["community_id"]
                .dropna()
                .value_counts()
                .head(2)
                .index
                .tolist()
            )
        except Exception:
            gexf_top2 = []

        m_top1 = metrics_df.loc[metrics_df["rank"] == 1, "community_id"]
        m_top2 = metrics_df.loc[metrics_df["rank"] == 2, "community_id"]
        m_top1_id = pd.to_numeric(m_top1.iloc[0], errors="coerce") if not m_top1.empty else np.nan
        m_top2_id = pd.to_numeric(m_top2.iloc[0], errors="coerce") if not m_top2.empty else np.nan

        if len(gexf_top2) >= 2 and pd.notna(m_top1_id) and pd.notna(m_top2_id):
            g1, g2 = gexf_top2[0], gexf_top2[1]
            if float(g1) == float(m_top1_id) and float(g2) == float(m_top2_id):
                print(f"[] {period} GEXF(louvain_community)  Top1/Top2  metrics.csv(rank=1/2)  {g1}, {g2}")
            else:
                print(
                    f"[warning] {period} Top1/Top2  \n"
                    f"  - metrics.csv: Top1={m_top1_id}, Top2={m_top2_id}\n"
                    f"  - gexf Top2 by node_count: Top1={g1}, Top2={g2}\n"
                    f"   metrics.csv  community_id  {out_col_name}   "
                )
        else:
            print(f"[note] {period} done Top1/Top2  GEXF  metrics information/  ")

        if out_col_name not in metrics_df.columns:
            metrics_df[out_col_name] = np.nan

        for r in (1, 2):
            rows = metrics_df[metrics_df["rank"] == r]
            if rows.empty:
                continue
            comm_id = rows["community_id"].iloc[0]
            comm_id_num = pd.to_numeric(comm_id, errors="coerce")
            if pd.isna(comm_id_num):
                print(f"[skip] {period} rank={r}  community_id : {comm_id}")
                continue

            comm_nodes = nodes_df[nodes_df["community_id"] == comm_id_num]
            mean_bias = float(comm_nodes["media_bias"].mean()) if not comm_nodes.empty else np.nan
            metrics_df.loc[metrics_df["rank"] == r, out_col_name] = mean_bias

        metrics_df.to_csv(metrics_csv_path, index=False, encoding="utf-8-sig")
        v1 = metrics_df.loc[metrics_df["rank"] == 1, out_col_name].iloc[0] if (metrics_df["rank"] == 1).any() else np.nan
        v2 = metrics_df.loc[metrics_df["rank"] == 2, out_col_name].iloc[0] if (metrics_df["rank"] == 2).any() else np.nan
        print(f"[done] {period}  {os.path.basename(metrics_csv_path)} Top1={v1} Top2={v2}")



import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import math


def _get_nice_max_scale(val):
    if val == 0 or pd.isna(val):
        return 0
    mag = 10 ** math.floor(math.log10(abs(val)))
    for multiplier in [1, 2, 4, 5, 8, 10]:
        if abs(val) <= multiplier * mag:
            return multiplier * mag if val > 0 else -multiplier * mag
    return 10 * mag if val > 0 else -10 * mag


def _radar_axis_config_from_metrics(combined_df):
    """Project workflow helper."""
    english_metrics = [
        "Nodes", "Edges", "Avg Degree",
        "Assortativity", "Clustering Coeff",
    ]
    custom_min_vals = [0, 0, 0, 0, 0]
    custom_max_vals = [
        _get_nice_max_scale(combined_df["node_count"].max()),
        _get_nice_max_scale(combined_df["edge_count"].max()),
        _get_nice_max_scale(combined_df["avg_degree"].max()),
        _get_nice_max_scale(combined_df["assortativity"].abs().max()),
        _get_nice_max_scale(combined_df["clustering_coefficient"].max()),
    ]
    include_media_mean = (
        "mean_media_bias" in combined_df.columns
        and combined_df["mean_media_bias"].notna().any()
    )
    if include_media_mean:
        english_metrics.append("Abs Mean Media Bias")
        custom_min_vals.append(0)
        custom_max_vals.append(
            _get_nice_max_scale(combined_df["mean_media_bias"].abs().max())
        )
    else:
        print(
            "[warning]  mean_media_bias  Step2 quarter bias   Step9 skip  "
            "radar_charts "
        )
    return english_metrics, custom_min_vals, custom_max_vals, include_media_mean


def _radar_raw_values_from_metrics_row(row, include_media_mean: bool):
    raw = [
        row["node_count"].iloc[0],
        row["edge_count"].iloc[0],
        row["avg_degree"].iloc[0],
        abs(row["assortativity"].iloc[0]) if pd.notna(row["assortativity"].iloc[0]) else np.nan,
        row["clustering_coefficient"].iloc[0],
    ]
    if include_media_mean:
        mb = row["mean_media_bias"].iloc[0] if "mean_media_bias" in row.columns else np.nan
        raw.append(abs(mb) if pd.notna(mb) else np.nan)
    return raw


# =============================================================================
# =============================================================================
def plot_multi_quarter_radar_charts_final():
    QUARTER_LIST = [
        "2019_12_2020_01_2020_02",
        "2020_03_2020_04_2020_05",
        "2020_06_2020_07_2020_08",
        "2020_09_2020_10",
        "2020_11_2020_12",
        "2021_01_2021_02"
    ]
    
    base_dir = TOP1_PCT_HUB_ROOT
    save_dir = os.path.join(TOP1_PCT_HUB_ROOT, "radar_charts")
    os.makedirs(save_dir, exist_ok=True)

    all_data_frames = []
    for quarter in QUARTER_LIST:
        file_path = os.path.join(base_dir, quarter, f"{quarter}_res1.0_seed42_top3_community_metrics.csv")
        
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                df = pd.read_csv(file_path)
                if df.empty:
                    print(f"skipdatafile: {file_path}")
                    continue
                    
                df['quarter'] = quarter
                all_data_frames.append(df)
            except pd.errors.EmptyDataError:
                print(f"skipfile: {file_path}")
        else:
            print(f"skip0file: {file_path}")

    if not all_data_frames:
        print("error readdata  filepath ")
        return

    combined_df = pd.concat(all_data_frames)

    english_metrics, custom_min_vals, custom_max_vals, include_media_mean = (
        _radar_axis_config_from_metrics(combined_df)
    )

    print(" ")
    for m, min_v, max_v in zip(english_metrics, custom_min_vals, custom_max_vals):
        print(f"{m}: [{min_v}, {max_v}]")

    angles = np.linspace(0, 2 * np.pi, len(english_metrics), endpoint=False).tolist()
    angles += angles[:1]

    color_map = {1: (0.2, 0.4, 0.6), 2: (0.8, 0.4, 0.4)}
    label_map = {1: "Rank 1", 2: "Rank 2"}

    for df in all_data_frames:
        quarter = df['quarter'].iloc[0]
        fig, ax = plt.subplots(subplot_kw={'polar': True}, figsize=(10, 10))
        
        for rank in [1, 2]:
            row = df[df['rank'] == rank]
            if row.empty: continue
            
            raw_vals = _radar_raw_values_from_metrics_row(row, include_media_mean)
            
            scaled_vals = []
            for i, v in enumerate(raw_vals):
                denom = custom_max_vals[i] - custom_min_vals[i]
                scaled_vals.append((v - custom_min_vals[i]) / denom if denom != 0 else 0.5)
            
            plot_vals = scaled_vals + [scaled_vals[0]]
            ax.plot(angles, plot_vals, label=label_map[rank], color=color_map[rank], linewidth=3)
            ax.fill(angles, plot_vals, color=color_map[rank], alpha=0.1)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(english_metrics, fontsize=11, fontweight='bold')
        ax.tick_params(axis='x', pad=30)
        
        ax.set_ylim(0, 1)
        ax.set_yticklabels([]) 
        
        for i in range(len(english_metrics)):
            grid_vals = np.linspace(custom_min_vals[i], custom_max_vals[i], 5)
            for k, val in enumerate(grid_vals):
                if k == 0: continue 
                radius = k / 4.0
                
                if abs(val) >= 1000000: label_text = f"{val/1e6:g}M"
                elif abs(val) >= 1000: label_text = f"{val/1e3:g}K"
                elif 0 < abs(val) < 0.01: label_text = f"{val:.4f}"
                elif type(val) == np.float64 and abs(val) < 10: label_text = f"{val:.2f}"
                else: label_text = f"{val:g}"
                
                ax.text(angles[i], radius, label_text, ha='center', va='center', 
                        fontsize=8, color='gray', fontweight='semibold',
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

        plt.title(f"Community Metrics Comparison\n{quarter}", pad=40, fontsize=16)
        plt.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1))
        
        save_path = os.path.join(save_dir, f"{quarter}_radar_unified.png")
        plt.savefig(save_path, dpi=1200, bbox_inches='tight')
        plt.close()
        print(f"generateradar_charts(Top1+Top2 mean_media_bias): {save_path}")


def plot_multi_quarter_radar_charts_final_without_axes():
    QUARTER_LIST = [
        "2019_12_2020_01_2020_02",
        "2020_03_2020_04_2020_05",
        "2020_06_2020_07_2020_08",
        "2020_09_2020_10",
        "2020_11_2020_12",
        "2021_01_2021_02"
    ]
    
    base_dir = TOP1_PCT_HUB_ROOT
    save_dir = os.path.join(TOP1_PCT_HUB_ROOT, "radar_charts")
    os.makedirs(save_dir, exist_ok=True)

    all_data_frames = []
    for quarter in QUARTER_LIST:
        file_path = os.path.join(base_dir, quarter, f"{quarter}_res1.0_seed42_top3_community_metrics.csv")
        
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                df = pd.read_csv(file_path)
                if df.empty:
                    print(f"skipdatafile: {file_path}")
                    continue
                    
                df['quarter'] = quarter
                all_data_frames.append(df)
            except pd.errors.EmptyDataError:
                print(f"skipfile: {file_path}")
        else:
            print(f"skip0file: {file_path}")

    if not all_data_frames:
        print("error readdata  filepath ")
        return

    combined_df = pd.concat(all_data_frames)

    english_metrics, custom_min_vals, custom_max_vals, include_media_mean = (
        _radar_axis_config_from_metrics(combined_df)
    )

    print(" ")
    for m, min_v, max_v in zip(english_metrics, custom_min_vals, custom_max_vals):
        print(f"{m}: [{min_v}, {max_v}]")

    angles = np.linspace(0, 2 * np.pi, len(english_metrics), endpoint=False).tolist()
    angles += angles[:1]

    color_map = {1: (0.2, 0.4, 0.6), 2: (0.8, 0.4, 0.4)}
    label_map = {1: "Rank 1", 2: "Rank 2"}

    for df in all_data_frames:
        quarter = df['quarter'].iloc[0]
        fig, ax = plt.subplots(subplot_kw={'polar': True}, figsize=(10, 10))
        
        for rank in [1, 2]:
            row = df[df['rank'] == rank]
            if row.empty: continue
            
            raw_vals = _radar_raw_values_from_metrics_row(row, include_media_mean)
            
            scaled_vals = []
            for i, v in enumerate(raw_vals):
                denom = custom_max_vals[i] - custom_min_vals[i]
                scaled_vals.append((v - custom_min_vals[i]) / denom if denom != 0 else 0.5)
            
            plot_vals = scaled_vals + [scaled_vals[0]]
            ax.plot(angles, plot_vals, label=label_map[rank], color=color_map[rank], linewidth=3)
            ax.fill(angles, plot_vals, color=color_map[rank], alpha=0.1)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([])
        ax.tick_params(axis='x', pad=30)
        
        ax.set_ylim(0, 1)
        ax.set_yticklabels([])
        
        # plt.title(...)
        # plt.legend(...)
        
        save_path = os.path.join(save_dir, f"{quarter}_radar_unified_notext.png")
        plt.savefig(save_path, dpi=1200, bbox_inches='tight')
        plt.close()
        print(f"generateradar_charts: {save_path}")


# =============================================================================
# =============================================================================
if __name__ == "__main__":
    QUARTER_LIST = _top1pct_default_quarters()
    LOUVAIN_RESOLUTION = DEFAULT_LOUVAIN_RESOLUTION
    LOUVAIN_SEED = DEFAULT_LOUVAIN_SEED
    PARAMS_TAG = f"res{LOUVAIN_RESOLUTION}_seed{LOUVAIN_SEED}"

    for period in QUARTER_LIST:
        process_quarterly_analysis_without_diameter_top1_percent(
            period, resolution=LOUVAIN_RESOLUTION, random_seed=LOUVAIN_SEED
        )
    print(">>> Step 1 done  / Hub / Top3  / GEXF <<<\n")

    append_quarterly_bias_scores_to_community_nodes_top1_percent(
        periods=QUARTER_LIST, partition_source="csv"
    )
    print(">>> Step 2 done  bias <<<\n")

    classify_community_nodes_by_bias_top1_percent(
        periods=QUARTER_LIST
    )
    print(">>> Step 3 done political_biasclassify <<<\n")

    write_classified_node_attributes_to_gexf_top1_percent(
        QUARTER_LIST, gexf_params_tag=PARAMS_TAG
    )
    print(">>> Step 4 done  with_political_attributes.gexf <<<\n")

    # analyze_community_political_distribution_Top1Percent(QUARTER_LIST)

    # plot_quarterly_media_bias_distribution_top1_top2_Top1Percent(QUARTER_LIST)
    # plot_quarterly_media_bias_distribution_without_axes_top1_percent(QUARTER_LIST)

    # extract_top3_community_core_nodes_by_quarter_Top1Percent(
    #     QUARTER_LIST, resolution=LOUVAIN_RESOLUTION, random_seed=LOUVAIN_SEED
    # )
    # extract_top3_communities_hub_keywords_tfidf_by_quarter_Top1Percent(
    #     QUARTER_LIST, resolution=LOUVAIN_RESOLUTION, random_seed=LOUVAIN_SEED
    # )

    append_top1_top2_mean_media_bias_to_top3_metrics_csv_Top1Percent(
        QUARTER_LIST, gexf_params_tag=PARAMS_TAG, metrics_params_tag=PARAMS_TAG
    )
    print(">>> Step 9 done media bias <<<\n")

    plot_multi_quarter_radar_charts_final()
    print(">>> Step 10 done  3c radar_charts  <<<")
    plot_multi_quarter_radar_charts_final_without_axes()
    print(">>> Step 10b done  3c radar_charts  <<<")

