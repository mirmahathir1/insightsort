print("Code started")
import cli_only
import argparse
import sys
import duckdb
from pathlib import Path
from algorithms import minhash_builder, table_description_builder
from algorithms import semantic_type_extractor
semantic_distance_threshold_for_datalake_column_mapping = 0.9
cosine_distance_threshold_for_existing_column_mapping = 0.2

parser = argparse.ArgumentParser(
	description="InsightSort (CLI) — discover interesting sort attributes and optionally augment data from a data-lake."
)
parser.add_argument("--datalakes-root", default="datalakes", help="Root folder containing data-lakes (default: %(default)s)")
parser.add_argument("--lake", help="Name of the data-lake to use (folder under datalakes-root). If omitted, you'll be prompted.")
parser.add_argument("--input-table", help="Stem name of input CSV (under <lake>/input_tables). If omitted, you'll be prompted.")
parser.add_argument("--export", help="Path to save the final output CSV (optional).")
parser.add_argument("--print-json", action="store_true", help="Print the chosen suggestion record as JSON before running SQL.")
args = parser.parse_args()

datalakes_root = Path("data" / args.datalakes_root)
if not datalakes_root.exists():
	cli_only.eprint(f"❌ Datalakes root not found: {datalakes_root}")
	sys.exit(1)

# Pick data-lake
available = cli_only.list_dir_names(datalakes_root)
if not available:
	cli_only.eprint(f"❌ No data-lakes found under {datalakes_root}")
	sys.exit(1)

if args.lake and args.lake in available:
	lake_name = args.lake
else:
	if args.lake and args.lake not in available:
		cli_only.eprint(f"⚠️ Requested lake '{args.lake}' not found; choose interactively.")
	lake_name = cli_only.choose_from_list("Select a data-lake:", available)

lake_dir   = datalakes_root / lake_name
index_dir  = lake_dir / "index_files"

cli_only.print_rule(f"Loading data-lake '{lake_name}'")
data_lake = cli_only.load_datalake_tables(lake_dir)
print(f"Loaded {len(data_lake)} tables from {lake_dir/'all_tables'}.")

cli_only.print_rule("Ensuring indexes")
cli_only.ensure_indexes(data_lake, index_dir)
print("✅ Indexes present.")

# Connect DuckDB; register 'input_table' later
con = duckdb.connect()

# Select & load input table

input_name, df_input, input_path = cli_only.select_input_table(lake_dir, prefer=args.input_table)

input_table_minhash = minhash_builder.build_minhashes(datalake={'input_table': df_input}, parallel_enabled=False)['input_table']

all_minhashes = minhash_builder.load_minhashes(save_dir=index_dir)

table_descriptions = table_description_builder.load_table_descriptions(save_dir=index_dir)

all_semantic_types = semantic_type_extractor.load_semantic_types(index_dir)

suggestions_df, _ = cli_only.generate_numeric_column_suggestions(
    input_table=df_input,
	input_table_minhash=input_table_minhash,
	all_minhashes=all_minhashes,
	data_lake=data_lake,
	table_descriptions=table_descriptions,
	cosine_distance_threshold_for_existing_column_mapping=cosine_distance_threshold_for_existing_column_mapping,
	semantic_types=all_semantic_types
)

print("💡 Suggestions generated:")

cli_only.print_df(suggestions_df[['Augmented Column', 'description', 'Source Table', 'interestingness']], max_rows=1000)
