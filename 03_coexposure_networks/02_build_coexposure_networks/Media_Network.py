import os
import glob
import sys
from pathlib import Path
import pandas as pd
import networkx as nx
from itertools import combinations

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















DATA_ROOT_DIR = str(rp.MEDIA_COEXPOSURE_DATA)
RESULT_DIR = str(rp.COEXPOSURE_RESULT_DIR)

TOP_N_PER_CATEGORY = 25

TOP_K_EDGES = 10

TARGET_CATEGORIES = [
    "Center", "Extreme Bias Left", "Extreme Bias Right", "Fake News",
    "Left", "Left Leaning", "Right", "Right Leaning"
]

COLOR_MAP = {
    'Extreme Bias Left': {'r': 0, 'g': 51, 'b': 102, 'a': 1.0},
    'Left': {'r': 51, 'g': 102, 'b': 153, 'a': 1.0},
    'Left Leaning': {'r': 181, 'g': 216, 'b': 243, 'a': 1.0},
    'Center': {'r': 240, 'g': 230, 'b': 140, 'a': 1.0},
    'Right Leaning': {'r': 255, 'g': 153, 'b': 153, 'a': 1.0},
    'Right': {'r': 204, 'g': 102, 'b': 102, 'a': 1.0},
    'Extreme Bias Right': {'r': 139, 'g': 26, 'b': 26, 'a': 1.0},
    'Fake News': {'r': 139, 'g': 26, 'b': 26, 'a': 1.0},
    'Unknown': {'r': 128, 'g': 128, 'b': 128, 'a': 1.0}
}


# ===========================================

def load_data(root_dir):
    print("Step 1: Loading data...")
    media_users = {}
    media_bias = {}

    if not os.path.exists(root_dir):
        print(f"Error: Path '{root_dir}' does not exist.")
        return {}, {}

    for category in TARGET_CATEGORIES:
        cat_path = os.path.join(root_dir, category)
        if not os.path.isdir(cat_path):
            continue

        csv_files = glob.glob(os.path.join(cat_path, '*.csv'))
        # print(f"  - Reading {category}: {len(csv_files)} files.")

        for file_path in csv_files:
            media_name = os.path.splitext(os.path.basename(file_path))[0]
            try:
                df = pd.read_csv(file_path, header=None, usecols=[0], dtype=str)
                users = set(df.iloc[:, 0].dropna().unique())
                if len(users) > 0:
                    media_users[media_name] = users
                    media_bias[media_name] = category
            except Exception as e:
                print(f"    Error reading {file_path}: {e}")

    print(f"Loaded {len(media_users)} media outlets in total.")
    return media_users, media_bias


def build_network_top_k(media_users, media_bias, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"\nStep 2: Filtering Top {TOP_N_PER_CATEGORY} Media per Category...")

    media_counts = []
    for m, users in media_users.items():
        media_counts.append({
            'name': m,
            'bias': media_bias[m],
            'count': len(users)
        })
    df_counts = pd.DataFrame(media_counts)

    top_media_df = df_counts.groupby('bias', group_keys=False).apply(
        lambda x: x.sort_values('count', ascending=False).head(TOP_N_PER_CATEGORY)
    )

    valid_media_set = set(top_media_df['name'].values)

    print(f"  Total nodes retained: {len(valid_media_set)}")
    print(f"  Breakdown by category:")
    print(top_media_df['bias'].value_counts())

    csv_path = os.path.join(output_dir, 'all_media_jaccard_values.csv')
    df_edges = pd.DataFrame()

    if os.path.exists(csv_path):
        print(f"\nStep 3: Found existing edge file. Loading...")
        df_full = pd.read_csv(csv_path, dtype={'source': str, 'target': str, 'weight': float})

        mask = df_full['source'].isin(valid_media_set) & df_full['target'].isin(valid_media_set)
        df_edges = df_full[mask].copy()
        print(f"  Filtered to {len(df_edges)} edges among top media.")

    else:
        print(f"\nStep 3: Calculating Jaccard Similarities for Top Media...")
        media_list = list(valid_media_set)
        all_edges = []

        total_pairs = len(list(combinations(media_list, 2)))
        print(f"  Processing {total_pairs} pairs...")

        for name_i, name_j in combinations(media_list, 2):
            users_i = media_users[name_i]
            users_j = media_users[name_j]

            union = len(users_i.union(users_j))
            if union > 0:
                intersection = len(users_i.intersection(users_j))
                if intersection > 0:
                    jaccard = intersection / union
                    all_edges.append({
                        'source': name_i,
                        'target': name_j,
                        'weight': jaccard,
                        'raw_intersection': intersection
                    })

        df_edges = pd.DataFrame(all_edges)

    if df_edges.empty:
        print("No edges found between selected media.")
        return

    print(f"\nStep 4: Keeping Top {TOP_K_EDGES} strongest edges for each media...")

    df_forward = df_edges[['source', 'target', 'weight', 'raw_intersection']].copy()
    df_backward = df_edges[['target', 'source', 'weight', 'raw_intersection']].copy()
    df_backward.columns = ['source', 'target', 'weight', 'raw_intersection']

    df_combined = pd.concat([df_forward, df_backward])

    df_top_k = df_combined.groupby('source', group_keys=False).apply(
        lambda x: x.sort_values('weight', ascending=False).head(TOP_K_EDGES)
    )

    print(f"  Edges retained (directional count): {len(df_top_k)}")

    print(f"\nStep 5: Generating Graph...")
    G = nx.Graph()

    for media_name in valid_media_set:
        user_count = len(media_users[media_name])
        bias = media_bias[media_name]
        color = COLOR_MAP.get(bias, COLOR_MAP["Unknown"])

        G.add_node(
            media_name,
            political_bias=bias,
            user_count=user_count,
            viz={'color': color}
        )

    for _, row in df_top_k.iterrows():
        G.add_edge(
            row['source'],
            row['target'],
            weight=float(row['weight']),
            raw_intersection=int(row['raw_intersection'])
        )

    print(f"Network constructed: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")

    G.remove_nodes_from(list(nx.isolates(G)))
    print(f"After removing isolates: {G.number_of_nodes()} nodes.")

    if len(G) > 0:
        largest_cc = max(nx.connected_components(G), key=len)
        G_final = G.subgraph(largest_cc).copy()
        print(f"Extracted Largest Connected Component: {G_final.number_of_nodes()} nodes.")
    else:
        G_final = G

    output_filename = f'media_network_CatTop{TOP_N_PER_CATEGORY}_EdgeTop{TOP_K_EDGES}.gexf'
    output_path = os.path.join(output_dir, output_filename)
    nx.write_gexf(G_final, output_path)
    print(f"Graph saved to: {output_path}")


def main():
    media_users, media_bias = load_data(DATA_ROOT_DIR)
    if not media_users:
        return
    build_network_top_k(media_users, media_bias, RESULT_DIR)


if __name__ == "__main__":
    main()