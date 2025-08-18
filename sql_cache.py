from pathlib import Path
import json
import hashlib
import pickle
import pandas as pd

def read_augmented_sql_cache(augment_data: dict, cached: bool):
    """
    Load augmented SQL + DataFrame from a pickle cache if available and requested.
    Otherwise, compute using compute_fn(), persist to cache, and return the result.

    Payload format: {"sql": str, "df": pandas.DataFrame}
    """
    if not cached:
        return None
    cache_dir = Path.cwd() / "results/augmented_sql_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key_src = json.dumps(augment_data, sort_keys=True, default=str)

    cache_hash = hashlib.sha256(cache_key_src.encode("utf-8")).hexdigest()
    cache_path = cache_dir / f"{cache_hash}.pkl"

    # Fast path: return cached when requested and present
    if cached and cache_path.exists():
        with open(cache_path, "rb") as f:
            payload = pickle.load(f)
        return payload["sql"], payload["df"]

    return None

def save_augmented_sql_cache(augment_data: dict, sql: str, df: pd.DataFrame, cached):
    """
    Save augmented SQL + DataFrame to a pickle cache.
    Cache location: ./llmcache/augmented_sql_cache/<sha256(augment_data)>.pkl
    Payload format: {"sql": str, "df": pandas.DataFrame}
    """
    cache_dir = Path.cwd() / "results/augmented_sql_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key_src = json.dumps(augment_data, sort_keys=True, default=str)

    cache_hash = hashlib.sha256(cache_key_src.encode("utf-8")).hexdigest()
    cache_path = cache_dir / f"{cache_hash}.pkl"

    payload = {"sql": sql, "df": df}

    with open(cache_path, "wb") as f:
        pickle.dump(payload, f)