import pandas as pd
import os
from embedding_utils import embed_column_values, embed_column_semantic_type, embed_text
from index_builder import HNSWIndex

# Load Index files
def load_indexes(index_dir: str):
    join_index = HNSWIndex(dim=384)
    join_index.load(os.path.join(index_dir, "joinability_index"))

    semantic_index = HNSWIndex(dim=384)
    semantic_index.load(os.path.join(index_dir, "semantic_index"))

    return join_index, semantic_index


def find_joinable_columns(input_col_values: list[str], join_index: HNSWIndex, top_k = 5):
    """Find data lake columns with values similar to the input column (join candidates)"""
    emb = embed_column_values(input_col_values)
    if emb is None:
        return None
    return join_index.query(emb, k=top_k)

def find_semantic_matches(suggested_attribute: str, semantic_index: HNSWIndex, top_k=5):
    """Find data lake columns that semantically match an LLM-suggested attribute"""
    emb = embed_text(suggested_attribute)
    if emb is None:
        return []
    return semantic_index.query(emb, k=top_k)


def discover_augmentable_column(
    suggested_attribute: str,
    input_table: pd.DataFrame,
    datalake: dict[str, pd.DataFrame],
    semantic_index: HNSWIndex,
    join_index: HNSWIndex,
    top_k=5
    ):


    '''Try to find joinable column in the datalake that provides the suggested attribute'''
    
    semantic_matches = semantic_index.query(embed_text(suggested_attribute), k = top_k)

    for (table_name, attr_col), sem_dist in semantic_matches:
        if sem_dist < 0.6:
            datalake_table = datalake.get(table_name)
            if datalake_table is None:
                continue

            for input_col in input_table.columns:
                input_vals = input_table[input_col].dropna().unique().tolist()
                if not input_vals:
                    continue
                
                join_vector = embed_column_values(input_vals)
                if join_vector is None:
                    continue

                join_matches = join_index.query(join_vector, k=top_k)

                for (join_table, join_col), join_dist in join_matches:
                    if join_dist <= 0.7:
                        if join_table == table_name and join_col in datalake_table.columns:

                            # Found joinable path
                            return {
                                "suggested_attribute": suggested_attribute,
                                "matched_table": join_table,
                                "matched_column": attr_col,
                                "join_key_input": input_col,
                                "join_key_datalake": join_col,
                                "semantic_distance": sem_dist,
                                "join_distance": join_dist
                            }

    return None


