#!/usr/bin/env python3
# insightsort_cli.py — CLI version of InsightSort (no Streamlit)

import sys
import argparse
from pathlib import Path

import duckdb
import pandas as pd
from algorithms import table_description_builder, minhash_builder

from algorithms import semantic_type_extractor, suggestion_engine
from algorithms import index_builder
import helpers
import pandas_helper



def select_input_table(lake_dir: Path, prefer: str | None = None) -> tuple[str, pd.DataFrame, Path]:
    input_dir = lake_dir / "input_tables"
    files = helpers.list_csv_files(input_dir)
    if not files:
        raise RuntimeError(f"No input tables found in {input_dir} (need *.csv).")
    names = [p.stem for p in files]
    if prefer and prefer in names:
        chosen_name = prefer
    else:
        chosen_name = helpers.choose_from_list("Select an input table:", names)
    chosen_file = next(p for p in files if p.stem == chosen_name)
    df = pandas_helper.read_csv_safely(chosen_file)
    return chosen_name, df, chosen_file

def main():
    cosine_distance_threshold_for_existing_column_mapping = 0.2
    suggestion_deduplication_semantic_type_distance_threshold = 0.3
    min_joinability_distance_threshold = 0.99

    parser = argparse.ArgumentParser(
        description="InsightSort (CLI) — discover interesting sort attributes and optionally augment data from a data-lake."
    )
    parser.add_argument("--datalakes-root", default="datalakes", help="Root folder containing data-lakes (default: %(default)s)")
    parser.add_argument("--lake", help="Name of the data-lake to use (folder under datalakes-root). If omitted, you'll be prompted.")
    parser.add_argument("--input-table", help="Stem name of input CSV (under <lake>/input_tables). If omitted, you'll be prompted.")
    parser.add_argument("--export", help="Path to save the final output CSV (optional).")
    parser.add_argument("--print-json", action="store_true", help="Print the chosen suggestion record as JSON before running SQL.")
    args = parser.parse_args()

    print("Welcome to InsightSort CLI! This tool helps you discover interesting sort attributes and augment data from a data-lake.")
    datalakes_root = Path(args.datalakes_root)
    if not datalakes_root.exists():
        helpers.eprint(f"❌ Datalakes root not found: {datalakes_root}")
        sys.exit(1)

    # Pick data-lake
    helpers.print_rule("Available data-lakes:")
    available = helpers.list_dir_names(datalakes_root)
    if not available:
        helpers.eprint(f"❌ No data-lakes found under {datalakes_root}")
        sys.exit(1)

    if args.lake and args.lake in available:
        lake_name = args.lake
    else:
        if args.lake and args.lake not in available:
            helpers.eprint(f"⚠️ Requested lake '{args.lake}' not found; choose interactively.")
        lake_name = helpers.choose_from_list("Select a data-lake:", available)

    lake_dir   = datalakes_root / lake_name
    index_dir  = lake_dir / "index_files"

    helpers.print_rule(f"Loading data-lake '{lake_name}'")
    data_lake = pandas_helper.load_datalake_tables(lake_dir)
    print(f"Loaded {len(data_lake)} tables from {lake_dir/'all_tables'}.")

    helpers.print_rule("Ensuring indexes")
    index_builder.ensure_indexes(data_lake, index_dir)
    print("✅ Indexes present.")

    con = duckdb.connect()

    # Select & load input table

    input_name, df_input, input_path = select_input_table(lake_dir, prefer=args.input_table)
    # Register the input table in DuckDB
    con.unregister("input_table") if "input_table" in con.execute("SHOW TABLES").df().values else None
    con.register("input_table", df_input)

    table_descriptions = table_description_builder.load_table_descriptions(index_dir)

    # Generate suggestions
    input_table_minhash = minhash_builder.build_minhashes(datalake={'input_table': df_input}, parallel_enabled=False)['input_table']
    all_minhashes = minhash_builder.load_minhashes(index_dir)
    all_semantic_types = semantic_type_extractor.load_semantic_types(index_dir)

    semantic_type_embeddings = semantic_type_extractor.load_semantic_type_embeddings(index_dir)

    suggestions_df, augmentation_cache = suggestion_engine.generate_numeric_column_suggestions(
        input_table=df_input,
        input_table_minhash=input_table_minhash,
        all_minhashes=all_minhashes,
        data_lake=data_lake,
        table_descriptions=table_descriptions,
        cosine_distance_threshold_for_existing_column_mapping=cosine_distance_threshold_for_existing_column_mapping,
        suggestion_deduplication_semantic_type_distance_threshold=suggestion_deduplication_semantic_type_distance_threshold,
        semantic_types=all_semantic_types,
        semantic_type_embeddings=semantic_type_embeddings,
        min_joinability_distance_threshold=min_joinability_distance_threshold,
        )

    # Write augmentations and metadata to txt files before showing suggestions
    augment_dir = Path.cwd() / "results" / f"augmentations_txt_{lake_name}"
    # Clear the augment_dir if it exists
    if augment_dir.exists() and augment_dir.is_dir():
        for f in augment_dir.iterdir():
            if f.is_file():
                f.unlink()
    augment_dir.mkdir(parents=True, exist_ok=True)

    # Also store the full suggestions dataframe in the augmentations folder
    # Print selected columns of suggestions_df to a text file, similar to print_df
    selected_cols = ['Augmented Column', 'description', 'Source Table', 'interestingness']
    suggestions_txt_path = augment_dir / "suggestions.txt"
    with open(suggestions_txt_path, "w", encoding="utf-8") as f:
        sub_df = suggestions_df[selected_cols]
        max_rows = 10000
        if len(sub_df) > max_rows:
            f.write(sub_df.head(max_rows).to_string(index=True))
            f.write(f"\n... ({len(sub_df) - max_rows} more rows)\n")
        else:
            f.write(sub_df.to_string(index=True))
    print(f"✅ Saved summary to {suggestions_txt_path}")

    # Iterate over suggestions_df to generate output files for all suggestions, with order number prefix
    for order_num, (_, row) in enumerate(suggestions_df.iterrows(), 1):
        base_col = row["base_column"]
        datalake_column = row["datalake_column"]
        datalake_table = row["datalake_table"]

        aug = augmentation_cache[(base_col, datalake_table, datalake_column)]

        filename = augment_dir / f"{order_num}_augmentation_{base_col}__{datalake_column}.txt"

        _, out_df = suggestion_engine.generate_augmented_sql_and_run(con, df_input, data_lake, aug, cached=False)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"Base Column:                      {base_col}\n")
            f.write(f"Description:                      {row['description']}\n")
            f.write(f"Interestingness:                  {row['interestingness']}\n")
            f.write(f"Suggested Attribute:              {aug['datalake_column']}\n")
            f.write(f"Matched Table / Column:           {aug['datalake_table']} / {aug['datalake_column']}\n")
            f.write(f"Join Keys (input \u2194 lake):    {aug['join_key_input']} <-> {aug['join_key_datalake']}\n")

            join_distance = aug['join_distance']
            f.write(f"Join Distance:           {join_distance}\n")
            f.write("\n--- Augmented Table (first 20 rows) ---\n")

            f.write(out_df.to_string(index=False))

    print(f"✅ Augmentation details written to {augment_dir}/<order>_augmentation_<base_col>__<sort_attr>.txt for each augmentation.")

if __name__ == "__main__":
    main()
