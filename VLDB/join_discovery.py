import pandas as pd
import os
from embedding_utils import embed_column_values, embed_column_semantic_type, embed_text
from index_builder import HNSWIndex
import pprint

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


# def discover_augmentable_column(
#     suggested_attribute: str,
#     input_table: pd.DataFrame,
#     datalake: dict[str, pd.DataFrame],
#     semantic_index: HNSWIndex,
#     join_index: HNSWIndex,
#     top_k=5
#     ):


#     '''Try to find joinable column in the datalake that provides the suggested attribute'''
    
#     semantic_matches = semantic_index.query(embed_text(suggested_attribute), k = top_k)

#     for (table_name, attr_col), sem_dist in semantic_matches:
#         if sem_dist < 0.6:
#             datalake_table = datalake.get(table_name)
#             if datalake_table is None:
#                 continue

#             for input_col in input_table.columns:
#                 input_vals = input_table[input_col].dropna().unique().tolist()
#                 if not input_vals:
#                     continue
                
#                 join_vector = embed_column_values(input_vals)
#                 if join_vector is None:
#                     continue

#                 join_matches = join_index.query(join_vector, k=top_k)

#                 for (join_table, join_col), join_dist in join_matches:
#                     if join_dist <= 0.7:
#                         if join_table == table_name and join_col in datalake_table.columns:

#                             # Found joinable path
#                             return {
#                                 "suggested_attribute": suggested_attribute,
#                                 "matched_table": join_table,
#                                 "matched_column": attr_col,
#                                 "join_key_input": input_col,
#                                 "join_key_datalake": join_col,
#                                 "semantic_distance": sem_dist,
#                                 "join_distance": join_dist
#                             }

#     return None


from typing import Optional, Dict, Any, Tuple, List
import numpy as np
import pandas as pd
from numpy.linalg import norm
import prompts
import llm_utils
import semantic_type

# ------------------------------------------------------------------
def _cosine_distance(a: np.ndarray, b: np.ndarray, eps: float = 1e-9) -> float:
    """
    Normalized cosine distance in the range [0, 1].

    - 0 → vectors are identical (cos θ = 1)
    - 1 → vectors point in exactly opposite directions (cos θ = –1)

    Parameters
    ----------
    a, b : np.ndarray
        1-D vectors of equal length.
    eps : float, optional
        Small constant to avoid division by zero when a or b is the zero vector.

    Returns
    -------
    float
        The normalized cosine distance between *a* and *b*.
    """
    sim = np.dot(a, b) / (norm(a) * norm(b) + eps)   # cosine similarity ∈ [–1, 1]
    dist = 0.5 * (1.0 - sim)                         # rescale to [0, 1]
    return float(np.clip(dist, 0.0, 1.0))
# ------------------------------------------------------------------

def infer_semantic_types_for_df(df: pd.DataFrame) -> Dict[str, str]:
    """
    Return a mapping  {column_name → semantic_type_text}  for *df*.

    It mirrors the logic in `_build_semantic_type_index` but keeps everything
    in-memory (no disk I/O):

      1. Builds a prompt with `prompts.generate_semantic_type_prompt`.
      2. Calls the LLM.
      3. Parses the JSON payload the model returns.
      4. Aligns keys back to the *exact* column names (difflib).

    Every column is guaranteed to appear exactly once in the result.
    """
    prompt        = prompts.generate_semantic_type_prompt(df)
    gpt_response  = llm_utils.call_gpt(prompt) or "{}"
    raw           = llm_utils.parse_suggestion(gpt_response)
    aligned_types = semantic_type.align_semantic_types(raw, df)
    return aligned_types

def discover_augmentable_column(
    suggested_attribute: str,
    input_table: pd.DataFrame,
    datalake: Dict[str, pd.DataFrame],
    semantic_index,
    join_index,
    semantic_type_index: Dict[str, Dict[str, str]],
    top_k: int = 5,
) -> Optional[Dict[str, Any]]:
    '''Try to find joinable column in the datalake that provides the suggested attribute'''
    
    input_table_semantic_types = infer_semantic_types_for_df(df=input_table)

    input_table_semantic_type_embeddings = {}
    for column in input_table.columns:
        input_table_semantic_type_embeddings[column] = embed_text(input_table_semantic_types[column])

    semantic_matches = semantic_index.query(embed_text(suggested_attribute), k = top_k)

    for (table_name, attr_col), sem_dist in semantic_matches:
        if sem_dist < 0.6:
            datalake_table = datalake.get(table_name)
            if datalake_table is None:
                continue

            attr_col_sem_type_embedding = embed_text(semantic_type_index[table_name][attr_col])
            column_already_exists = False
            for input_col_name, input_col_embedding in input_table_semantic_type_embeddings.items():
                cosine_distance = _cosine_distance(attr_col_sem_type_embedding, input_col_embedding)
                if cosine_distance < 0:
                    column_already_exists = True
                    break
            if column_already_exists:
                print(f"column already exists: new column - {table_name}.{attr_col}, already existing column - {input_col_name}")
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
                            joinable_path = {
                                "suggested_attribute": suggested_attribute,
                                "matched_table": join_table,
                                "matched_column": attr_col,
                                "join_key_input": input_col,
                                "join_key_datalake": join_col,
                                "semantic_distance": sem_dist,
                                "join_distance": join_dist
                            }

                            # Found joinable path
                            return joinable_path

    # Nothing suitable found
    return None
