import hnswlib
import os
import numpy as np
import pickle
import pandas as pd
from embedding_utils import embed_column_values, embed_column_semantic_type
import prompts
import llm_utils
import semantic_type
import json

class HNSWIndex:
    def __init__(self, dim, space="cosine"):
        self.index = hnswlib.Index(space=space, dim=dim)
        self.data = {}  # id -> (table, column)

    def build(self, vectors, meta, ef=200, M=16):
        self.index.init_index(max_elements=len(vectors), ef_construction=ef, M=M)
        self.index.add_items(vectors, ids=np.arange(len(vectors)))
        self.data = {i: meta[i] for i in range(len(meta))}

    def save(self, path):
        self.index.save_index(path + ".bin")
        with open(path + "_meta.pkl", "wb") as f:
            pickle.dump(self.data, f)
    
    def load(self, path):
        self.index.load_index(path + ".bin")
        with open(path + "_meta.pkl", "rb") as f:
            self.data = pickle.load(f)
    
    def query(self, vector, k = 5):
        labels, distances = self.index.knn_query(vector, k=k)
        return [(self.data[idx], dist) for idx, dist in zip(labels[0], distances[0])]

# ───────────────────────── Build helpers ──────────────────────────
def _build_join_index(datalake: dict[str, pd.DataFrame], save_dir: str, *,
                      force: bool = False, verbose: bool = True) -> None:
    join_dir = os.path.join(save_dir, "joinability_index")
    os.makedirs(join_dir, exist_ok=True)
    prefix = os.path.join(join_dir, "index")            # -> index.bin / index_meta.pkl

    if (not force
        and os.path.exists(prefix + ".bin")
        and os.path.exists(prefix + "_meta.pkl")):
        if verbose:
            print("✅ Joinability index already exists. Skipping.")
        return

    join_vectors, join_meta = [], []
    for table, df in datalake.items():
        for col in df.columns:
            vals = df[col].dropna().unique().tolist()
            vec = embed_column_values(vals)
            if vec is not None:
                join_vectors.append(vec)
                join_meta.append((table, col))

    if not join_vectors:
        if verbose:
            print("⚠️ No join vectors; joinability index not built.")
        return

    idx = HNSWIndex(dim=join_vectors[0].shape[0])
    idx.build(join_vectors, join_meta)
    idx.save(prefix)
    if verbose:
        print(f"💾 Saved joinability index → {join_dir}")


def _build_semantic_index(datalake: dict[str, pd.DataFrame], save_dir: str, *,
                          force: bool = False, verbose: bool = True) -> None:
    sem_dir = os.path.join(save_dir, "semantic_index")
    os.makedirs(sem_dir, exist_ok=True)
    prefix = os.path.join(sem_dir, "index")             # -> index.bin / index_meta.pkl

    if (not force
        and os.path.exists(prefix + ".bin")
        and os.path.exists(prefix + "_meta.pkl")):
        if verbose:
            print("✅ Semantic index already exists. Skipping.")
        return

    sem_vectors, sem_meta = [], []
    for table, df in datalake.items():
        for col in df.columns:
            vals = df[col].dropna().unique().tolist()
            vec = embed_column_semantic_type(col, vals)
            if vec is not None:
                sem_vectors.append(vec)
                sem_meta.append((table, col))

    if not sem_vectors:
        if verbose:
            print("⚠️ No semantic vectors; semantic index not built.")
        return

    idx = HNSWIndex(dim=sem_vectors[0].shape[0])
    idx.build(sem_vectors, sem_meta)
    idx.save(prefix)
    if verbose:
        print(f"💾 Saved semantic index → {sem_dir}")

def _build_semantic_type_index(
    datalake: dict[str, pd.DataFrame],
    save_dir: str,
    *,
    force: bool = False,
    verbose: bool = True,
) -> None:
    """
    Use GPT + alignment to assign a textual semantic type to every column,
    then dump the whole mapping as JSON.
    """
    type_dir  = os.path.join(save_dir, "semantic_type_index")
    os.makedirs(type_dir, exist_ok=True)
    json_path = os.path.join(type_dir, "types.json")

    if not force and os.path.exists(json_path):
        if verbose: print("✅ Semantic-type index already exists. Skipping.")
        return

    types_index: dict[str, dict[str, str]] = {}

    for table, df in datalake.items():
        prompt       = prompts.generate_semantic_type_prompt(df)
        gpt_response = llm_utils.call_gpt(prompt) or "{}"
        raw          = llm_utils.parse_suggestion(gpt_response)
        aligned      = semantic_type.align_semantic_types(raw, df)      # guarantees every column
        types_index[table] = aligned
        if verbose: print(f"🔎 Finished {table}")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(types_index, f, ensure_ascii=False, indent=2)

    if verbose: print(f"💾 Saved semantic-type index → {json_path}")


# ───────────────────────── Load helper ────────────────────────────
def load_indexes(index_dir: str, dim: int = 384):
    """
    Returns
    -------
    (join_index, semantic_index, semantic_type_dict)
    """
    join_prefix = os.path.join(index_dir, "joinability_index", "index")
    sem_prefix  = os.path.join(index_dir, "semantic_index",     "index")
    type_path   = os.path.join(index_dir, "semantic_type_index", "types.json")

    join_index = HNSWIndex(dim=dim); join_index.load(join_prefix)
    semantic_index = HNSWIndex(dim=dim); semantic_index.load(sem_prefix)

    if os.path.exists(type_path):
        with open(type_path, "r", encoding="utf-8") as f:
            semantic_types = json.load(f)
    else:
        semantic_types = {}

    return join_index, semantic_index, semantic_types


def build_indexes_from_datalake(datalake: dict[str, pd.DataFrame], save_dir: str,
                                *, force: bool = False, verbose: bool = True) -> None:
    """Wrapper: create the two index types (joinability & semantic)."""
    os.makedirs(save_dir, exist_ok=True)
    _build_join_index(datalake, save_dir, force=force, verbose=verbose)
    _build_semantic_index(datalake, save_dir, force=force, verbose=verbose)
    _build_semantic_type_index(datalake, save_dir, force=force, verbose=verbose)

