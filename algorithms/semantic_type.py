import difflib
from typing import Dict
import pandas as pd

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
