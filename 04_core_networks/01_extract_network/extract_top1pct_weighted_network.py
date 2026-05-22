import networkx as nx
import pandas as pd
import os
import csv
import re
import gc
import traceback
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import sys
import igraph as ig
from pathlib import Path

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


def _three_month_dirs(month: str):
    return [
        str(rp.THREE_PARTS_OUTPUT / "twitter_url" / f"output_{month}"),
        str(rp.THREE_PARTS_OUTPUT / "without_url" / f"output_{month}"),
        str(rp.THREE_PARTS_OUTPUT / "external_url" / f"output_{month}"),
    ]







def extract_and_save_top1_percent_weighted_degree_network():
    QUARTERS = [
        "2019_12_2020_01_2020_02",
        "2020_03_2020_04_2020_05",
        "2020_06_2020_07_2020_08",
        "2020_09_2020_10",
        "2020_11_2020_12",
        "2021_01_2021_02"
    ]
    
    BASE_INPUT_DIRS = [
        str(rp.THREE_PARTS_OUTPUT / "twitter_url" / "output_{}"),
        str(rp.THREE_PARTS_OUTPUT / "without_url" / "output_{}"),
        str(rp.THREE_PARTS_OUTPUT / "external_url" / "output_{}"),
    ]
    
    RESULT_DIR = str(rp.TOP1_PERCENT_NETWORK_DIR)
    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)
        
    TOP_PERCENT = 0.01 
    # ===========================================

    for period_name in QUARTERS:
        print(f"\n{'='*30}")
        print(f"processingprocess: {period_name}")
        print(f":  {int(TOP_PERCENT*100)}% ")
        print(f"{'='*30}")

        sub_months = re.findall(r'\d{4}_\d{2}', period_name)
        print(f" -> month: {sub_months}")

        all_edges = []
        for month in sub_months:
            for base_dir_template in BASE_INPUT_DIRS:
                data_dir = base_dir_template.format(month)
                if not os.path.exists(data_dir):
                    continue
                
                for file in os.listdir(data_dir):
                    if file.endswith('.csv'):
                        file_path = os.path.join(data_dir, file)
                        try:
                            df = pd.read_csv(file_path, usecols=['retweeted_user_id', 'retweet_origin_user_id'], dtype=str)
                            df.dropna(inplace=True)
                            edges = list(df.itertuples(index=False, name=None))
                            all_edges.extend(edges)
                        except Exception as e:
                            print(f"    [Warning] read {file}: {e}")
        
        print(f" -> dataread : {len(all_edges)}")

        if len(all_edges) == 0:
            print(" -> [skip] quarterdata missingmonthdirectory CSV  quarter ")
            continue

        print(" -> processing...")
        g = ig.Graph.TupleList(all_edges, directed=False)
        del all_edges
        gc.collect() 
        
        g.es['weight'] = 1

        print(f"    [] : {g.vcount()}, (): {g.ecount()}")

        print(" -> processing...")
        
        g.simplify(multiple=True, loops=True, combine_edges={'weight': 'sum'})
        
        print(f"    [] : {g.vcount()}, (): {g.ecount()}")
        
        print(" -> processing (LCC)...")
        components = g.components()
        largest = components.giant()
        
        del g, components
        gc.collect()
        
        print(f"    [LCC] : {largest.vcount()}, : {largest.ecount()}")

        if largest.vcount() == 0:
            print(" -> [skip]  quarter ")
            del largest
            gc.collect()
            continue

        # =======================================================
        # =======================================================
        print(f" -> processing Top {int(TOP_PERCENT*100)}%...")
        
        degrees = largest.degree()
        
        degree_threshold = np.percentile(degrees, (1.0 - TOP_PERCENT) * 100)
        
        print(f"    []  1% : {degree_threshold}")
        
        nodes_to_keep = [v.index for v, d in zip(largest.vs, degrees) if d >= degree_threshold]
        
        top_degree_subgraph = largest.subgraph(nodes_to_keep)
        
        del largest, degrees
        gc.collect()
        
        print(f"    [ Top 1% ] : {top_degree_subgraph.vcount()}, : {top_degree_subgraph.ecount()}")

        print(" -> processingsavefile...")
        
        node_file = os.path.join(RESULT_DIR, f"{period_name}_top1pct_nodes.csv")
        edge_file = os.path.join(RESULT_DIR, f"{period_name}_top1pct_edges.csv")
        
        sub_degrees = top_degree_subgraph.degree()
        nodes_df = pd.DataFrame({
            'user_id': top_degree_subgraph.vs['name'],
            'degree': sub_degrees
        })
        nodes_df.to_csv(node_file, index=False)
        
        edges_indices = top_degree_subgraph.get_edgelist()
        edges_weights = top_degree_subgraph.es['weight']
        
        source_ids = [top_degree_subgraph.vs[u]['name'] for u, v in edges_indices]
        target_ids = [top_degree_subgraph.vs[v]['name'] for u, v in edges_indices]
        
        edges_df = pd.DataFrame({
            'source': source_ids,
            'target': target_ids,
            'weight': edges_weights
        })
        edges_df = edges_df.sort_values(by='weight', ascending=False)
        
        edges_df.to_csv(edge_file, index=False)
        
        print(f" -> savedone: \n    : {node_file}\n    : {edge_file}")
        
        del top_degree_subgraph, nodes_df, edges_df
        gc.collect()








if __name__ == '__main__':
    extract_and_save_top1_percent_weighted_degree_network()


