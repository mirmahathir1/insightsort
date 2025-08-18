import difflib
from typing import Dict
import pandas as pd
import os
from algorithms import prompts
import llm_utils
import embedding_utils
import json
from tqdm import tqdm

def align_semantic_types(
    raw_result: Dict[str, str],
    df: pd.DataFrame,
) -> Dict[str, str]:
    """
    Force-align the model’s keys to the DataFrame’s exact column names.

    For each column, pick the semantic type whose returned key
    has the highest similarity (difflib ratio) to that column name.
    No similarity cutoff is applied.

    Parameters
    ----------
    raw_result : dict
        Parsed JSON from the model response.
    df : pd.DataFrame
        DataFrame whose columns we want as final keys.

    Returns
    -------
    Dict[str, str]
        Mapping {original_column_name: semantic_type}.
        Every column is guaranteed to appear exactly once.
    """
    original_cols = list(df.columns)

    # Fast exit if the model returned nothing
    if not raw_result:
        return {col: "unknown" for col in original_cols}

    model_keys = list(raw_result.keys())
    refined: Dict[str, str] = {}

    for col in original_cols:
        # Compute similarity between this column and every returned key
        best_key, best_ratio = None, -1.0
        for key in model_keys:
            ratio = difflib.SequenceMatcher(None, col.lower(), key.lower()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_key = key

        # Assign the semantic type from the best-matched key
        refined[col] = raw_result.get(best_key, "unknown")

    return refined

def does_semantic_type_file_exist(save_dir: str) -> bool:
    """
    Check if the semantic type file exists in the specified directory.

    Parameters
    ----------
    save_dir : str
        Directory where the semantic types are saved.

    Returns
    -------
    bool
        True if the semantic type file exists, False otherwise.
    """
    type_path = os.path.join(save_dir, "semantic_type_index", "types.json")
    return os.path.exists(type_path)

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
    aligned_types = align_semantic_types(raw, df)
    return aligned_types

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

    types_index: dict[str, dict[str, str]] = {}

    for table, df in datalake.items():
        prompt       = prompts.generate_semantic_type_prompt(df)
        gpt_response = llm_utils.call_gpt(prompt) or "{}"
        raw          = llm_utils.parse_suggestion(gpt_response)
        aligned      = align_semantic_types(raw, df)      # guarantees every column
        types_index[table] = aligned
        if verbose: print(f"🔎 Finished {table}")

    return types_index

def save_semantic_types(types_index: dict[str, dict[str, str]], save_dir: str, verbose: bool = True) -> None:
    type_dir  = os.path.join(save_dir, "semantic_type_index")
    os.makedirs(type_dir, exist_ok=True)
    json_path = os.path.join(type_dir, "types.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(types_index, f, ensure_ascii=False, indent=2)

    if verbose: print(f"💾 Saved semantic-type index → {json_path}")

def load_semantic_types(save_dir: str) -> dict[str, dict[str, str]]:
    """
    Load the semantic types from a JSON file.

    :param save_dir: Directory where the semantic types are saved.
    :return: Dictionary of table names to their semantic types.
    """
    input_path = os.path.join(save_dir, "semantic_type_index", "types.json")
    if not os.path.exists(input_path):
        print(f"No semantic types found at {input_path}. Returning empty dictionary.")
        return {}

    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_semantic_type_embeddings(input_table: pd.DataFrame) -> dict[str, list[float]]:
    input_table_semantic_types = infer_semantic_types_for_df(df=input_table)
    input_table_semantic_type_embeddings = {}
    for column in input_table.columns:
        input_table_semantic_type_embeddings[column] = embedding_utils.embed_text(input_table_semantic_types[column])
    return input_table_semantic_type_embeddings

def build_semantic_type_embeddings_for_datalake(
    semantic_types: dict[str, dict[str, str]]
) -> dict[str, dict[str, list[float]]]:
    """
    Build semantic type embeddings for each column in the datalake.

    :return: Dictionary mapping table names to their semantic type embeddings.
    """
    semantic_type_embeddings = {}
    for table_name, cols in tqdm(semantic_types.items()):
        embeddings = {col: embedding_utils.embed_text(semantic_types[table_name][col]) for col in cols}
        semantic_type_embeddings[table_name] = embeddings
    return semantic_type_embeddings

def save_semantic_type_embeddings(
    semantic_type_embeddings: dict[str, dict[str, list[float]]],
    save_dir: str,
    verbose: bool = True
) -> None:
    """
    Save the semantic type embeddings to a pickle file.

    :param semantic_type_embeddings: Dictionary of table names to their semantic type embeddings.
    :param save_dir: Directory where the embeddings will be saved.
    :param verbose: Whether to print status messages.
    """
    import pickle
    embeddings_path = os.path.join(save_dir, "semantic_type_index", "semantic_type_embeddings.pkl")
    os.makedirs(os.path.dirname(embeddings_path), exist_ok=True)
    with open(embeddings_path, "wb") as f:
        pickle.dump(semantic_type_embeddings, f)

    if verbose: print(f"💾 Saved semantic type embeddings → {embeddings_path}")

def does_semantic_type_embeddings_exist(save_dir: str) -> bool:
    """
    Check if the semantic type embeddings file exists in the specified directory.

    :param save_dir: Directory where the semantic type embeddings are saved.
    :return: True if the semantic type embeddings file exists, False otherwise.
    """
    embeddings_path = os.path.join(save_dir, "semantic_type_index", "semantic_type_embeddings.pkl")
    return os.path.exists(embeddings_path)

def load_semantic_type_embeddings(save_dir: str) -> dict[str, dict[str, list[float]]]:
    """
    Load the semantic type embeddings from a pickle file.

    :param save_dir: Directory where the semantic type embeddings are saved.
    :return: Dictionary of table names to their semantic type embeddings.
    """
    import pickle
    embeddings_path = os.path.join(save_dir, "semantic_type_index", "semantic_type_embeddings.pkl")

    with open(embeddings_path, "rb") as f:
        return pickle.load(f)