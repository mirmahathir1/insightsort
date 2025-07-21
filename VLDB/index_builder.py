import hnswlib
import os
import numpy as np
import pickle
import pandas as pd
from embedding_utils import embed_column_values, embed_column_semantic_type

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

def build_indexes_from_datalake(datalake: dict[str, pd.DataFrame], save_dir: str):
    join_vectors, join_meta = [], []
    semantic_vectors, semantic_meta = [], []

    for table_name, df in datalake.items():
        for col in df.columns:
            values = df[col].dropna().unique().tolist()

            jv = embed_column_values(values)
            sv = embed_column_semantic_type(col, values)

            if jv is not None:
                join_vectors.append(jv)
                join_meta.append((table_name, col))
            if sv is not None:
                semantic_vectors.append(sv)
                semantic_meta.append((table_name, col))

    os.makedirs(save_dir, exist_ok=True)
    join_index = HNSWIndex(dim=join_vectors[0].shape[0])
    join_index.build(join_vectors, join_meta)
    join_index.save(os.path.join(save_dir, "joinability_index"))

    semantic_index = HNSWIndex(dim=semantic_vectors[0].shape[0])
    semantic_index.build(semantic_vectors, semantic_meta)
    semantic_index.save(os.path.join(save_dir, "semantic_index"))

