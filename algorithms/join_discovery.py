import pandas as pd
from embedding_utils import embed_column_values, embed_text, _cosine_distance
from algorithms.index_builder import HNSWIndex
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd

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

def discover_join(
    datalake_table: str,
    datalake_column: str,
    input_table_minhash,
    input_table_semantic_type_embeddings,
    semantic_types: Dict[str, Dict[str, str]],
    minhashes,
    base_col,
    min_joinability_distance_threshold,

    cosine_distance_threshold_for_existing_column_mapping
) -> Optional[Dict[str, Any]]:

    attr_col_sem_type_embedding = embed_text(semantic_types[datalake_table][datalake_column])
    column_already_exists = False
    for input_col_name, input_col_embedding in input_table_semantic_type_embeddings.items():
        cosine_distance = _cosine_distance(attr_col_sem_type_embedding, input_col_embedding)
        if cosine_distance < cosine_distance_threshold_for_existing_column_mapping:
            column_already_exists = True
            break

    if column_already_exists:
        return None

    min_joinability_distance = 1
    best_datalake_join_key = None

    input_table_base_col_minhash = input_table_minhash[base_col]

    for col, minhash in minhashes[datalake_table].items():
        jaccard = input_table_base_col_minhash.jaccard(minhash)
        joinability_distance = 1 - jaccard
        if joinability_distance < min_joinability_distance:
            min_joinability_distance = joinability_distance
            best_datalake_join_key = col

    if best_datalake_join_key is None:
        return None

    if min_joinability_distance > min_joinability_distance_threshold:
        return None


    joinable_path = {
        "datalake_table": datalake_table,
        "datalake_column": datalake_column,
        "base_column": base_col,
        "join_key_input": base_col,
        "join_key_datalake": best_datalake_join_key,
        "join_distance": min_joinability_distance,
    }

    # Found joinable path
    return joinable_path


def discover_augmentable_column(
    suggested_attribute: str,
    input_table: pd.DataFrame,
    input_table_minhash,
    input_table_semantic_type_embeddings,
    datalake: Dict[str, pd.DataFrame],
    semantic_types: Dict[str, Dict[str, str]],
    minhashes,
    semantic_type_hnsw_index,
    base_col,
    top_k,
    min_joinability_distance_threshold,

    semantic_distance_threshold_for_datalake_column_mapping,
    cosine_distance_threshold_for_existing_column_mapping
) -> Optional[Dict[str, Any]]:
    '''Try to find joinable column in the datalake that provides the suggested attribute'''

    # semantic_distance_threshold_for_datalake_column_mapping = 0.4
    # cosine_distance_threshold_for_existing_column_mapping = 0.2
    # min_joinability_distance_threshold = 0.1

    # semantic_distance_threshold_for_datalake_column_mapping = 0.9
    # cosine_distance_threshold_for_existing_column_mapping = 0.2
    

    # semantic_matches = semantic_index.query(embed_text(suggested_attribute), k = top_k)
    semantic_matches = semantic_type_hnsw_index.query(embed_text(suggested_attribute), k=top_k)


    input_table_base_col_minhash = input_table_minhash[base_col]

    # _, _, input_table_base_col_minhash = index_builder.get_column_minhash(('input_table', base_col, input_table[base_col]), {"num_perm": 128, "seed": 1}, None)

    for (table_name, attr_col), sem_dist in semantic_matches:
        if sem_dist > semantic_distance_threshold_for_datalake_column_mapping:
            # print(f"Semantic distance {sem_dist} exceeds threshold for {table_name}.{attr_col}.")
            continue
        datalake_table = datalake.get(table_name)
        if datalake_table is None:
            print(f"Table {table_name} not found in datalake.")
            exit(0)

        attr_col_sem_type_embedding = embed_text(semantic_types[table_name][attr_col])
        column_already_exists = False
        for input_col_name, input_col_embedding in input_table_semantic_type_embeddings.items():
            cosine_distance = _cosine_distance(attr_col_sem_type_embedding, input_col_embedding)
            if cosine_distance < cosine_distance_threshold_for_existing_column_mapping:
                column_already_exists = True
                # print(f"column already exists: new column - {table_name}.{attr_col}, already existing column - {input_col_name}")
                # print("input column semantic type: ", input_table_semantic_types[input_col_name])
                # print("datalake column semantic type: ", semantic_type_index[table_name][attr_col])
                # print("cosine distance: ", cosine_distance)
                break

        if column_already_exists:
            continue

        input_vals = input_table[base_col].dropna().unique().tolist()
        if not input_vals:
            # print(f"No valid values found in input column {base_col}.")
            continue

        min_joinability_distance = 1
        best_datalake_join_key = None

        for col, minhash in minhashes[table_name].items():
            jaccard = input_table_base_col_minhash.jaccard(minhash)
            joinability_distance = 1 - jaccard
            if joinability_distance < min_joinability_distance:
                min_joinability_distance = joinability_distance
                best_datalake_join_key = col


        if best_datalake_join_key is None:
            # print(f"No suitable join key found in {table_name} for {base_col}.")
            continue

        if min_joinability_distance > min_joinability_distance_threshold:
            # print(f"Joinability distance {min_joinability_distance} exceeds threshold for {table_name}.{attr_col}.")
            continue

        if best_datalake_join_key == attr_col:
            # print(f"Join key {best_datalake_join_key} matches the suggested attribute {attr_col} in {table_name}.")
            continue

        joinable_path = {
            "suggested_attribute": suggested_attribute,
            "matched_table": table_name,
            "matched_column": attr_col,
            "join_key_input": base_col,
            "join_key_datalake": best_datalake_join_key,
            "semantic_distance": sem_dist,
            "join_distance": min_joinability_distance
        }

        # Found joinable path
        return joinable_path
            
    # print("_" * 80)
    # Nothing suitable found
    return None
