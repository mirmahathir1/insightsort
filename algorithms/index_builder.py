import hnswlib
import os
import numpy as np
import pickle
import pandas as pd
from algorithms.embedding_utils import embed_column_values, embed_column_semantic_type, embed_text
from algorithms import prompts
from algorithms import llm_utils
from algorithms import table_description_builder
from algorithms import minhash_builder
from algorithms import semantic_type_extractor
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

def _build_semantic_type_hnsw_index(save_dir: str, *,
                          force: bool = False, verbose: bool = True) -> None:
    sem_dir = os.path.join(save_dir, "semantic_type_index")
    os.makedirs(sem_dir, exist_ok=True)
    prefix = os.path.join(sem_dir, "index")             # -> index.bin / index_meta.pkl

    if (not force
        and os.path.exists(prefix + ".bin")
        and os.path.exists(prefix + "_meta.pkl")):
        if verbose:
            print("✅ Semantic type hnsw index already exists. Skipping.")
        return

    sem_vectors, sem_meta = [], []
    semantic_types = json.load(open(os.path.join(sem_dir, "types.json"), "r", encoding="utf-8"))

    for table, columns in semantic_types.items():
        for col, sem_type in columns.items():
            vec = embed_text(sem_type)
            sem_vectors.append(vec)
            sem_meta.append((table, col))

    idx = HNSWIndex(dim=sem_vectors[0].shape[0])
    idx.build(sem_vectors, sem_meta)
    idx.save(prefix)
    if verbose:
        print(f"💾 Saved semantic index → {sem_dir}")




# ───────────────────────── Load helper ────────────────────────────
def load_indexes(index_dir: str, dim: int = 384):
    """
    Returns
    -------
    (join_index, semantic_index, semantic_type_dict)
    """
    semantic_type_hnsw_path = os.path.join(index_dir, "semantic_type_index", "index")
    semantic_type_hnsw_index = HNSWIndex(dim=dim); semantic_type_hnsw_index.load(semantic_type_hnsw_path)

    semantic_types = semantic_type_extractor.load_semantic_types(save_dir=index_dir)
    all_minhashes = minhash_builder.load_minhashes(index_dir)
    all_table_descriptions = table_description_builder.load_table_descriptions(index_dir)

    return semantic_types, semantic_type_hnsw_index, all_minhashes, all_table_descriptions


def build_indexes_from_datalake(datalake: dict[str, pd.DataFrame], save_dir: str,
                                *, force: bool = False, verbose: bool = True) -> None:
    """Wrapper: create the two index types (joinability & semantic)."""
    os.makedirs(save_dir, exist_ok=True)
    _build_join_index(datalake, save_dir, force=force, verbose=verbose)
    _build_semantic_index(datalake, save_dir, force=force, verbose=verbose)

    if not semantic_type_extractor.does_semantic_type_file_exist(save_dir):
        semantic_types = semantic_type_extractor._build_semantic_type_index(datalake, save_dir, force=force, verbose=verbose)
        semantic_type_extractor.save_semantic_types(semantic_types, save_dir, verbose=verbose)


    semantic_types = semantic_type_extractor.load_semantic_types(save_dir)
    if not table_description_builder.does_table_descriptions_exist(save_dir):
        descriptions = table_description_builder.generate_all_table_descriptions(datalake, semantic_types)
        table_description_builder.save_table_descriptions(descriptions, save_dir)

    _build_semantic_type_hnsw_index(save_dir, force=force, verbose=verbose)

    if not minhash_builder.does_minhashes_exist(save_dir):
        minhashes = minhash_builder.build_minhashes(datalake, parallel_enabled=True)
        minhash_builder.save_minhashes(minhashes, save_dir)

    if not table_description_builder.does_table_descriptions_exist(save_dir):
        descriptions = table_description_builder.generate_all_table_descriptions(datalake, semantic_types)
        table_description_builder.save_table_descriptions(descriptions, save_dir)

