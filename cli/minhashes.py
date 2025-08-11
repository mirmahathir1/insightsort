import os
import pickle
import pandas as pd
from datasketch import MinHash

def get_minhashes(table, dataframe):
    col_min_hash = []
    columns = []
    for column in dataframe.columns:
        col_min_hash += [(column,MinHash())]
        columns += ["\"" + column + "\""]

    for row_index, row in dataframe.iterrows():
        for index in range(len(row)):
            if pd.notna(row[index]):
                col_min_hash[index][1].update(str(row[index]).encode('utf8'))
    column_minhashes = {}
    for single_col_hash in col_min_hash:
        column_name = single_col_hash[0]
        minhash = single_col_hash[1]
        column_minhashes[column_name] = minhash
    return {table: column_minhashes}

def _build_minhashes(datalake: dict[str, pd.DataFrame], save_dir: str, force: bool = False, verbose: bool = True) -> None:
    if not force and os.path.exists(os.path.join(save_dir, "minhashes", "minhashes.pickle")):
        print("⚠️ Minhashes already exist; skipping.")
        return
    column_minhashes = {}
    for table, df in datalake.items():
        column_minhashes.update(get_minhashes(table, df))

    minhash_dir = os.path.join(save_dir, "minhashes")
    os.makedirs(minhash_dir, exist_ok=True)
    minhash_path = os.path.join(minhash_dir, "minhashes.pickle")
    with open(minhash_path, "wb") as f:
        pickle.dump(column_minhashes, f)
    print(f"💾 Saved minhashes → {minhash_path}")