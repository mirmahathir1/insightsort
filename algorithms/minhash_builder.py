# ─────────────────────── Loader for minhashes ───────────────────
def load_minhashes(save_dir: str):
	"""
	Loads minhashes from disk.
	Returns: {table: {column: MinHash}}
	"""
	minhash_path = os.path.join(save_dir, "minhashes", "minhashes.pickle")
	if not os.path.exists(minhash_path):
		raise FileNotFoundError(f"Minhashes file not found at {minhash_path}")
	with open(minhash_path, "rb") as f:
		minhashes = pickle.load(f)
	if not isinstance(minhashes, dict):
		raise ValueError("Minhashes should be a dictionary of {table: {column: MinHash}}")
	return minhashes
from datasketch import MinHash
import pandas as pd
import os
import pickle
from custom_lib import parallel

# ───────────────────────── Column-level worker ──────────────────────────────
def get_column_minhash(arg, com_arg, com_arg_batch):
	"""
	arg: (table_name: str, column_name: str, series_like: pd.Series or Iterable)
	returns: (table_name, column_name, MinHash)
	"""
	table, col, values = arg

	# You can pass num_perm/seed via com_arg if you want determinism
	num_perm = (com_arg or {}).get("num_perm", 128)
	seed     = (com_arg or {}).get("seed", 1)

	mh = MinHash(num_perm=num_perm, seed=seed)

	# Fast path: drop NaNs -> strings -> bytes and update
	if isinstance(values, pd.Series):
		iterable = values.dropna().astype(str).values
	else:
		# Generic iterable
		iterable = (str(v) for v in values if pd.notna(v))

	for v in iterable:
		mh.update(v.encode("utf-8"))

	return (table, col, mh)

def build_minhashes(datalake: dict[str, pd.DataFrame], parallel_enabled=True):
	# Prepare column-level argument list
	arg_list = []
	for table, df in datalake.items():
		for col in df.columns:
			arg_list.append((table, col, df[col]))

	# Optional shared config for workers (deterministic MinHashes)
	com_arg = {"num_perm": 128, "seed": 1}

	# Run column-level parallelism
	results = parallel.execute(
		func=get_column_minhash,
		argument_list=arg_list,
		common_arguments=com_arg,
		parallel_enabled=parallel_enabled
	)

	# Fold back into nested dict: {table: {col: MinHash}}
	column_minhashes: dict[str, dict[str, MinHash]] = {}
	for table, col, mh in results:
		if table not in column_minhashes:
			column_minhashes[table] = {}
		column_minhashes[table][col] = mh

	return column_minhashes

# ─────────────────────── Builder using column parallelism ───────────────────
def _build_minhashes(datalake: dict[str, pd.DataFrame], save_dir: str):
	"""
	datalake: { table_name: DataFrame }
	Parallelizes across columns, aggregates to:
	  { table_name: { column_name: MinHash } }
	"""
	# check if minhashes already exist
	minhash_path = os.path.join(save_dir, "minhashes", "minhashes.pickle")
	if os.path.exists(minhash_path):
		print(f"✅ Minhashes already exist at {minhash_path}. Skipping.")
		return

	print("🔨 Building minhashes for datalake columns...")
	column_minhashes = build_minhashes(datalake)

	# Persist
	minhash_dir = os.path.join(save_dir, "minhashes")
	os.makedirs(minhash_dir, exist_ok=True)
	minhash_path = os.path.join(minhash_dir, "minhashes.pickle")
	with open(minhash_path, "wb") as f:
		pickle.dump(column_minhashes, f)
	print(f"💾 Saved minhashes → {minhash_path}")

	return column_minhashes
