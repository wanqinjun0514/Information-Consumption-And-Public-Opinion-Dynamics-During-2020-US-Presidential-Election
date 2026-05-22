"""Project workflow helper."""
from __future__ import annotations

import os
import sys
from itertools import combinations
from pathlib import Path

import networkx as nx
import pandas as pd

_rp = Path(__file__).resolve()
for _ in range(8):
    if (_rp / "repo_paths.py").exists():
        if str(_rp) not in sys.path:
            sys.path.insert(0, str(_rp))
        break
    _rp = _rp.parent
else:
    raise RuntimeError("Repository root not found; repo_paths.py is missing.")

import repo_paths as rp

_utils_dir = str(rp.DIR_03_POLITICIAN_COEXPOSURE_SCRIPTS)
if _utils_dir not in sys.path:
    sys.path.insert(0, _utils_dir)
from politician_coexposure_utils import INFLUENCED_SUFFIX, parse_influenced_set_filename

DATA_DIR = str(rp.POLITICIAN_INFLUENCED_SETS)
RESULT_DIR = str(rp.COEXPOSURE_RESULT_DIR)

NODE_TOP_PERCENTILE = 0.8
TOP_K_EDGES = 10

COLOR_MAP = {
    "Left": {"r": 51, "g": 102, "b": 153, "a": 1.0},
    "Center": {"r": 240, "g": 230, "b": 140, "a": 1.0},
    "Right": {"r": 204, "g": 102, "b": 102, "a": 1.0},
    "Unknown": {"r": 128, "g": 128, "b": 128, "a": 1.0},
}


def load_influenced_sets(root_dir: str) -> tuple[dict[str, set[str]], dict[str, str]]:
    print("[Step4] user...")
    pol_users: dict[str, set[str]] = {}
    pol_bias: dict[str, str] = {}

    if not os.path.isdir(root_dir):
        print(f"directory: {root_dir}")
        return {}, {}

    for file_name in os.listdir(root_dir):
        if file_name.startswith("._") or not file_name.endswith(INFLUENCED_SUFFIX):
            continue
        parsed = parse_influenced_set_filename(file_name)
        if not parsed:
            continue
        pol_id, bias = parsed
        path = os.path.join(root_dir, file_name)
        try:
            df = pd.read_csv(path, usecols=["retweeted_user_id"], dtype={"retweeted_user_id": "str"})
        except ValueError:
            df = pd.read_csv(path, header=None, dtype=str)
            df.columns = ["retweeted_user_id"]
        users = set(df["retweeted_user_id"].dropna().astype(str))
        if users:
            pol_users[pol_id] = users
            pol_bias[pol_id] = bias

    print(f"[Step4]  {len(pol_users)} politician")
    return pol_users, pol_bias


def load_edges_from_step3(
    csv_path: Path,
    top_nodes: set[str],
) -> pd.DataFrame:
    """Project workflow helper."""
    df = pd.read_csv(csv_path, dtype={"politician_id_1": str, "politician_id_2": str})
    df = df.rename(
        columns={
            "politician_id_1": "source",
            "politician_id_2": "target",
            "common_user_count": "weight",
        }
    )
    df["source"] = df["source"].astype(str).str.strip()
    df["target"] = df["target"].astype(str).str.strip()
    mask = df["source"].isin(top_nodes) & df["target"].isin(top_nodes)
    df = df.loc[mask].copy()
    df["raw_intersection"] = df["weight"]
    return df


def compute_jaccard_edges(pol_users: dict[str, set[str]], node_ids: list[str]) -> pd.DataFrame:
    rows = []
    for id_i, id_j in combinations(node_ids, 2):
        u_i, u_j = pol_users[id_i], pol_users[id_j]
        inter = len(u_i & u_j)
        if inter == 0:
            continue
        union = len(u_i | u_j)
        rows.append(
            {"source": id_i, "target": id_j, "weight": inter / union, "raw_intersection": inter}
        )
    return pd.DataFrame(rows)


def filter_top_k_per_node(df_edges: pd.DataFrame, top_k: int) -> pd.DataFrame:
    if df_edges.empty:
        return df_edges
    df_forward = df_edges.copy()
    df_backward = df_edges.rename(columns={"source": "target", "target": "source"})
    df_forward["original_index"] = df_edges.index
    df_backward["original_index"] = df_edges.index
    df_combined = pd.concat([df_forward, df_backward])
    top_k_indices = df_combined.groupby("source", group_keys=False).apply(
        lambda x: x.sort_values("weight", ascending=False).head(top_k)
    )
    return df_edges.loc[list(set(top_k_indices["original_index"].values))].copy()


def build_network(pol_users: dict[str, set[str]], pol_bias: dict[str, str], output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    user_counts = {pid: len(u) for pid, u in pol_users.items()}
    sorted_pids = sorted(user_counts, key=user_counts.get, reverse=True)
    num_keep = max(1, int(len(sorted_pids) * NODE_TOP_PERCENTILE))
    top_nodes = set(sorted_pids[:num_keep])
    print(f"[Step4]  Top {NODE_TOP_PERCENTILE:.0%}: {len(top_nodes)}/{len(pol_users)} ")

    step3_path = rp.POLITICIAN_PAIRWISE_EDGES_CSV
    if step3_path.is_file():
        print(f"[Step4]  Step3 edge_list: {step3_path}")
        df_edges = load_edges_from_step3(step3_path, top_nodes)
    else:
        print("[Step4]  Step3 edge_list  Jaccard...")
        df_edges = compute_jaccard_edges(pol_users, list(top_nodes))

    if df_edges.empty:
        print("[Step4]  ")
        return

    final_edges = filter_top_k_per_node(df_edges, TOP_K_EDGES)
    print(f"[Step4] Top-{TOP_K_EDGES}/  {len(final_edges)} ")

    g = nx.Graph()
    for pol_id in top_nodes:
        g.add_node(
            str(pol_id),
            label=str(pol_id),
            political_bias=pol_bias.get(pol_id, "Unknown"),
            user_count=user_counts.get(pol_id, 0),
            viz={"color": COLOR_MAP.get(pol_bias.get(pol_id, "Unknown"), COLOR_MAP["Unknown"])},
        )

    for _, row in final_edges.iterrows():
        g.add_edge(
            str(row["source"]),
            str(row["target"]),
            weight=float(row["weight"]),
            raw_intersection=int(row.get("raw_intersection", 0)),
        )

    g.remove_nodes_from(list(nx.isolates(g)))
    if g.number_of_nodes() > 0:
        largest = max(nx.connected_components(g), key=len)
        g = g.subgraph(largest).copy()
        print(f"[Step4] : {g.number_of_nodes()} , {g.number_of_edges()} ")

    out_name = f"politician_network_NodesTop{int(NODE_TOP_PERCENTILE * 100)}_EdgesTop{TOP_K_EDGES}.gexf"
    out_path = os.path.join(output_dir, out_name)
    nx.write_gexf(g, out_path)
    print(f"[Step4] save -> {out_path}")


def main() -> None:
    pol_users, pol_bias = load_influenced_sets(DATA_DIR)
    if not pol_users:
        return
    build_network(pol_users, pol_bias, RESULT_DIR)


if __name__ == "__main__":
    main()
