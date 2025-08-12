# This file handles generating one line description for a table using semantic types and values

from algorithms.llm_utils import call_gpt
import pandas as pd
import json
import math
from custom_lib import utils
import os
import pprint
from algorithms import llm_utils
from algorithms.embedding_utils import embed_text
import faiss

def build_table_description_prompt(
    df: pd.DataFrame,
    table_name: str,
    semantic_types: dict[str, dict[str, str]],
    *,
    top_k: int = 3,
    max_value_len: int = 40,
) -> str:
    """
    Return a triple-quoted prompt string for ChatGPT to generate a single-line description of a table.
    Uses semantic_types[table_name] values instead of original column names.
    """

    # Map column name → semantic type label
    col_name_map = semantic_types.get(table_name, {})
    
    def _safe_str(x) -> str:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return ""
        s = str(x).replace("\n", " ").replace("\r", " ").strip()
        return (s[: max_value_len - 1] + "…") if len(s) > max_value_len else s

    preview_block = ""
    for col in df.columns:
        semantic_type = col_name_map[col]
        values = df[col].dropna().unique()[:top_k]
        values_str = ", ".join(_safe_str(v) for v in values)
        preview_block += f"{semantic_type}: {values_str}\n"

    return f"""
You are given metadata about a database table and some sample values. 
Write a concise, single-sentence description of what this table represents and the kind of data it contains. 
Focus on meaning, not internal pipeline details. 
Avoid listing every column; summarize the table's purpose and typical content in one line.

TABLE COLUMNS AND SAMPLE VALUES:

{preview_block}

Output format (strict JSON):
{{
  "table": "{table_name}",
  "description": "<one-line description>"
}}

Requirements:
- The JSON must be valid and on its own (no extra text before/after) and there should be no ```json annotations.
- "description" must be a single line (no newlines), <= 200 characters if possible.
- Do NOT invent columns that are not present; use the provided context.
"""

def generate_all_table_descriptions(all_dataframes: dict[str, pd.DataFrame], all_semantic_types: dict[str, dict[str, str]]) -> dict[str, str]:
    """
    Generate a description for each table in the provided dataframes.
    
    :param all_dataframes: Dictionary of table names to their corresponding DataFrames.
    :param all_semantic_types: Dictionary of table names to their semantic types.
    :return: Dictionary mapping table names to their descriptions.
    """
    descriptions = {}
    
    for table_name, df in all_dataframes.items():
        if table_name not in all_semantic_types:
            print(f"Warning: No semantic types found for table '{table_name}'. Skipping.")
            continue
        
        prompt = build_table_description_prompt(df, table_name, all_semantic_types)
        print(prompt)
        gpt_output = call_gpt(prompt)
        print(gpt_output)  # For debugging purposes
        if gpt_output:
            parsed_output = llm_utils.extract_json_object(gpt_output)
            description = parsed_output["description"]
            descriptions[table_name] = description.strip()
        else:
            descriptions[table_name] = "Description generation failed."

    return descriptions

def save_table_descriptions(descriptions: dict[str, str], save_dir: str) -> None:
    """
    Save the generated table descriptions to a JSON file.
    
    :param descriptions: Dictionary of table names to their descriptions.
    :param save_dir: Directory where the descriptions will be saved.
    """
    output_path = os.path.join(save_dir, "table_descriptions.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(descriptions, f, ensure_ascii=False, indent=2)
    print(f"Table descriptions saved to {output_path}.")

def load_table_descriptions(save_dir: str) -> dict[str, str]:
    """
    Load table descriptions from a JSON file.
    
    :param save_dir: Directory where the descriptions are saved.
    :return: Dictionary of table names to their descriptions.
    """
    input_path = os.path.join(save_dir, "table_descriptions.json")
    
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)

def does_table_descriptions_exist(save_dir: str) -> bool:
    """
    Check if the table descriptions file exists.
    
    :param save_dir: Directory where the descriptions are saved.
    :return: True if the file exists, False otherwise.
    """
    input_path = os.path.join(save_dir, "table_descriptions.json")
    return os.path.exists(input_path)

def build_table_clusters_using_table_description_embedding(
    table_descriptions: dict[str, str],
    n_clusters: int = 10,
    verbose: bool = False
) -> list[str]:
    """
    Build clusters of table descriptions using their embeddings.
    
    :param save_dir: Directory where the descriptions are saved.
    :param table_descriptions: Dictionary of table names to their descriptions.
    :param n_clusters: Number of clusters to form.
    :param verbose: Whether to print debug information.
    :return: List of cluster labels for each table.
    """
    if not table_descriptions:
        return []

    # Embed the descriptions
    descriptions_list = list(table_descriptions.values())
    embeddings = embed_text(descriptions_list)

    # Build FAISS index
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # Perform clustering
    _, labels = faiss.kmeans(embeddings, n_clusters, max_iter=20, verbose=verbose)

    # Map labels back to table names
    clustered_tables = {table_name: labels[i] for i, table_name in enumerate(table_descriptions.keys())}
    
    return clustered_tables

def table_filter_using_minhash(input_table_minhash, table_minhashes, minhash_jaccard_threshold):
    """
    input_table_minhash: dict[str, MinHash] consists of minhashes for each column in the input table.
    table_minhashes: dict[str, dict[str, MinHash]] consists of minhashes for each column in each table.
    table_descriptions: dict[str, str] consists of table names and their descriptions.
    minhash_jaccard_threshold: float, threshold for Jaccard similarity to consider a match.

    Returns a filtered list of table names which are joinable with the input table based on minhash similarity using Jaccard index.
    """
    # input_table_minhash: dict[str, MinHash] for each column in the input table
    # table_minhashes: dict[str, dict[str, MinHash]] for each table and its columns
    # minhash_jaccard_threshold: float

    def max_jaccard_for_table(input_minhashes, candidate_minhashes):
        # For each input column, find the max Jaccard similarity to any column in the candidate table
        max_scores = []
        for in_col, in_mh in input_minhashes.items():
            best = 0.0
            for cand_col, cand_mh in candidate_minhashes.items():
                score = in_mh.jaccard(cand_mh)
                if score > best:
                    best = score
            max_scores.append(best)
        return max_scores

    filtered_tables = []
    for table_name, candidate_minhashes in table_minhashes.items():
        # For each input column, get the best match in the candidate table
        max_scores = max_jaccard_for_table(input_table_minhash, candidate_minhashes)
        # If any input column has a match above the threshold, consider the table joinable
        if any(score >= minhash_jaccard_threshold for score in max_scores):
            filtered_tables.append(table_name)

    return filtered_tables