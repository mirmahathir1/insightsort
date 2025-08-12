#!/usr/bin/env python3
# insightsort_cli.py — CLI version of InsightSort (no Streamlit)

import os
import sys
import argparse
import traceback
from pathlib import Path
import pprint
import json

import duckdb
import pandas as pd
from tqdm import tqdm
import codecs
from custom_lib import parallel
from algorithms import table_description_builder, minhash_builder
import time

# ── Your existing modules ─────────────────────────────────────────────────────
from algorithms import prompts, embedding_utils
from algorithms import infer_type
from algorithms.llm_utils import call_gpt, parse_suggestion
from algorithms.index_builder import build_indexes_from_datalake, load_indexes
from algorithms.join_discovery import discover_augmentable_column
from algorithms.semantic_score import (
    compute_semantic_interestingness,
    update_suggestions_with_semantic_scores,
)

from algorithms import semantic_type_extractor

from algorithms import index_builder
from difflib import SequenceMatcher

min_joinability_distance_threshold = 0.99

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def remove_non_utf8_lines(filename):
    with codecs.open(filename, 'r', encoding='utf-8', errors='ignore') as f_in:
        lines = f_in.readlines()

    with codecs.open(filename, 'w', encoding='utf-8') as f_out:
        for line in lines:
            try:
                line.encode('utf-8')
                f_out.write(line)
            except UnicodeEncodeError:
                continue

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)



def list_dir_names(d: Path) -> list[str]:
    return sorted([p.name for p in d.iterdir() if p.is_dir()]) if d.exists() else []

def list_csv_files(d: Path) -> list[Path]:
    return sorted(d.glob("*.csv")) if d.exists() else []

def choose_from_list(prompt_text: str, options: list[str]) -> str:
    if not options:
        raise RuntimeError("No options to choose from.")
    print(f"\n{prompt_text}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        choice = input("Enter choice number: ").strip()
        if not choice.isdigit():
            print("Please enter a valid number.")
            continue
        idx = int(choice)
        if 1 <= idx <= len(options):
            return options[idx - 1]
        print("Out of range. Try again.")

def print_rule(title: str = ""):
    line = "─" * 80
    if title:
        print(f"\n{line}\n{title}\n{line}")
    else:
        print(f"\n{line}")

def yes_no(prompt_text: str, default_yes: bool = True) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"
    while True:
        ans = input(f"{prompt_text} {suffix} ").strip().lower()
        if ans == "" and default_yes:
            return True
        if ans == "" and not default_yes:
            return False
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'.")

def print_df(df: pd.DataFrame, max_rows: int = 30):
    if len(df) > max_rows:
        print(df.head(max_rows).to_string(index=True))
        print(f"... ({len(df) - max_rows} more rows)")
    else:
        print(df.to_string(index=True))

def export_df(df: pd.DataFrame, out_path: Path | None):
    if out_path is None:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"✅ Saved to {out_path}")

# ──────────────────────────────────────────────────────────────────────────────
# Core workflow
# ──────────────────────────────────────────────────────────────────────────────
def read_csv_safely(path: Path) -> pd.DataFrame:
    remove_non_utf8_lines(path)
    return pd.read_csv(path, on_bad_lines='skip', dtype=str)

# ───────────────────────── worker for one CSV ─────────────────────────
def _read_csv_worker(arg, common_arguments, common_args_for_batch):
    """
    arg: {"path": "<string path>", "name": "<table_name>"}
    returns:
      ("ok", name, df) on success
      ("err", name, "message") on failure
    """
    p = Path(arg["path"])
    name = arg["name"]
    try:
        df = read_csv_safely(p)
        return ("ok", name, df)
    except Exception as e:
        return ("err", name, f"{p.name}: {e}")

# ───────────────────── parallelized table loader ─────────────────────
def load_datalake_tables(lake_dir: Path) -> dict[str, pd.DataFrame]:
    """
    Reads all CSVs under lake_dir / 'all_tables' into DataFrames in parallel.
    Returns {table_name: dataframe}
    """
    all_tables_dir = lake_dir / "all_tables"
    tables: dict[str, pd.DataFrame] = {}

    csv_paths = list_csv_files(all_tables_dir)  # assumed to return Iterable[Path]
    argument_list = [{"path": str(p), "name": p.stem} for p in csv_paths]

    # If your executor supports worker config, pass via common_arguments
    results = parallel.execute(
        func=_read_csv_worker,
        argument_list=argument_list
    )

    for status, name, payload in results:
        if status == "ok":
            tables[name] = payload  # payload is the DataFrame
        else:
            # payload is the error message
            eprint(f"⚠️  Skipping {name}: {payload}")

    return tables

def ensure_indexes(data_lake: dict[str, pd.DataFrame], index_dir: Path):
    index_dir.mkdir(parents=True, exist_ok=True)
    build_indexes_from_datalake(data_lake, save_dir=index_dir)

def select_input_table(lake_dir: Path, prefer: str | None = None) -> tuple[str, pd.DataFrame, Path]:
    input_dir = lake_dir / "input_tables"
    files = list_csv_files(input_dir)
    if not files:
        raise RuntimeError(f"No input tables found in {input_dir} (need *.csv).")
    names = [p.stem for p in files]
    if prefer and prefer in names:
        chosen_name = prefer
    else:
        chosen_name = choose_from_list("Select an input table:", names)
    chosen_file = next(p for p in files if p.stem == chosen_name)
    df = read_csv_safely(chosen_file)
    return chosen_name, df, chosen_file

def split_dict(original_dict, n):
    """
    Split a dictionary into a list of dictionaries,
    each containing up to n key-value pairs.

    :param original_dict: dict, the dictionary to split
    :param n: int, max number of items in each split dictionary
    :return: list of dictionaries
    """
    if n <= 0:
        raise ValueError("n must be a positive integer")

    items = list(original_dict.items())
    return [dict(items[i:i + n]) for i in range(0, len(items), n)]

def generate_suggestions(input_table: pd.DataFrame, input_table_minhash, all_minhashes, data_lake: dict[str, pd.DataFrame], index_dir: Path, table_descriptions: list[dict[str, str]]) -> tuple[pd.DataFrame, dict]:
    """
    Calls LLM to generate suggestions, filters/augments where needed,
    enriches with semantic scores; returns (suggestions_df, augmentation_cache)
    """
    column_names = list(input_table.columns)

    joinable_tables = table_description_builder.table_filter_using_minhash(
        input_table_minhash=input_table_minhash,
        table_minhashes=all_minhashes,
        minhash_jaccard_threshold= 1 - min_joinability_distance_threshold
    )

    joinable_table_descriptions = {table: table_descriptions[table] for table in joinable_tables if table in table_descriptions}

    table_description_segments = split_dict(joinable_table_descriptions, 20)

    all_suggestions = {}
    print_rule("Calling LLM for suggestions")
    for segment in tqdm(table_description_segments):
        prompt = prompts.build_suggestion_prompt(input_table, column_names, other_table_descriptions=segment)

        gpt_response = call_gpt(prompt)
        table_description_segment_suggestions = parse_suggestion(gpt_response)
        for base_col, suggestions in table_description_segment_suggestions.items():
            if base_col not in all_suggestions:
                all_suggestions[base_col] = []
            all_suggestions[base_col].extend(suggestions)

    # Dump all suggestions as .json with indent=4 in file
    with open("all_suggestions.json", "w", encoding="utf-8") as f:
        json.dump(all_suggestions, f, indent=4, ensure_ascii=False)
    print("✅ Dumped all suggestions to all_suggestions.json")

    SIMILARITY_THRESHOLD = 0.92  # adjust as needed

    for base_col, suggestions in all_suggestions.items():
        unique_suggestions = []
        seen = []
        for s in suggestions:
            try:
                sort_attr = s["column"]
            except KeyError:
                print(f"⚠️ Missing 'column' in suggestion for base column '{base_col}': {s}")
                exit(0)
            is_similar = False
            for seen_attr in seen:
                similarity = SequenceMatcher(None, sort_attr.lower(), seen_attr.lower()).ratio()
                if similarity >= SIMILARITY_THRESHOLD:
                    is_similar = True
                    break
            if not is_similar:
                unique_suggestions.append(s)
                seen.append(sort_attr)
        all_suggestions[base_col] = unique_suggestions



    # exit(0)

    # Load indexes once
    join_index, semantic_index, semantic_types, semantic_type_hnsw_index = load_indexes(index_dir)

    augmentation_cache = {}
    rows = []

    # suggestions: { base_col: [ {column, description, interestingness, "column present in the table": "Yes"/"No"} ] }
    print_rule("Evaluating suggestions against the data lake")
    input_table_semantic_types = semantic_type_extractor.infer_semantic_types_for_df(df=input_table)
    input_table_semantic_type_embeddings = {}
    for column in input_table.columns:
        input_table_semantic_type_embeddings[column] = embedding_utils.embed_text(input_table_semantic_types[column])
    print("discover_augmentable_column")
    for base_col, sort_list in all_suggestions.items():
        for s in sort_list:
            # print(f"Evaluating suggestion for base column '{base_col}'")
            sort_attr   = s["column"]
            # print(f"  Sort Attribute: {sort_attr}")
            col_present = (s["column present in the table"] == "Yes")
            if not col_present:
                aug = discover_augmentable_column(
                    sort_attr,
                    input_table,                                  # input table
                    input_table_minhash,
                    input_table_semantic_type_embeddings,
                    data_lake,
                    semantic_index,
                    join_index,
                    semantic_types,
                    all_minhashes,
                    semantic_type_hnsw_index,
                    base_col,
                    5,
                    min_joinability_distance_threshold
                )
                if aug is None:
                    # skip suggestions that can't be satisfied
                    continue
                augmentation_cache[(base_col, sort_attr)] = aug

            rows.append({
                "Base Column":     base_col,
                "Sort Attribute":  sort_attr,
                "Description":     s.get("description", ""),
                "Interestingness": s.get("interestingness", ""),
                "Required Column": s["column"],
                "Column present":  "Yes" if col_present else "No",
                "Matched Column": sort_attr if col_present else aug['matched_column'],
                "Matched Table":   "input_table" if col_present else aug['matched_table'],
            })


    if len(rows) == 0:
        raise RuntimeError("No viable suggestions after augmentation checks.")

    suggestions_df = pd.DataFrame(rows)
    input_cols = list(suggestions_df.columns)
    print("update_suggestions_with_semantic_scores")
    suggestions_df = update_suggestions_with_semantic_scores(suggestions_df, input_cols)
    suggestions_df.index = suggestions_df.index + 1  # 1-based display
    return suggestions_df, augmentation_cache

def show_suggestions_and_pick(df_input: pd.DataFrame, suggestions_df: pd.DataFrame) -> tuple[int, pd.Series, float]:
    print_rule("🔍 Sorting Suggestions (sorted by Interestingness desc)")
    sorted_df = suggestions_df.sort_values(["Interestingness"], ascending=[False]).copy()
    # print rows of sorted_df as dictionaries
    print("\nSuggestions (as dictionaries):")
    for idx, row in sorted_df.iterrows():
        print(f"Suggestion {idx}: ")
        pprint.pprint(row.to_dict())


    # compute semantic utility overall
    input_columns = list(df_input.columns)
    candidate_columns = list(suggestions_df["Sort Attribute"])
    semantic_util = compute_semantic_interestingness(input_columns, candidate_columns)
    print(f"\nSemantic Utility score (0..1): {semantic_util:.4f}")

    # Let user select by display index (row number in sorted_df)
    # Build display options mapping back to original index
    # Prepare options as (original_idx, display_text) tuples
    options = []
    for idx, row in sorted_df.iterrows():
        display_text = f"{row['Base Column']:<20} | {row['Sort Attribute']:<30} | {row['Interestingness']:<30}| {row['Matched Table']:<20} | {row['Matched Column']:<20}"
        options.append((idx, display_text))

    # Print header
    print("\nChoose a suggestion:")
    print(f"{'No.':<4} | {'Base Column':<20} | {'Sort Attribute':<30} | {'Interestingness':<30} | {'Matched Table':<20} | {'Matched Column':<20}")
    print("-" * 140)

    # Print rows
    for i, (_, text) in enumerate(options, 1):
        print(f"{i:<4} | {text}")

    # Input loop
    while True:
        raw = input("Enter choice number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            choice_num = int(raw)
            original_idx, _ = options[choice_num - 1]
            chosen_row = suggestions_df.loc[original_idx]
            return original_idx, chosen_row, semantic_util
        print("Invalid choice. Try again.")


def generate_sort_sql_and_run(con, df_input: pd.DataFrame, selected_row: pd.Series) -> pd.DataFrame:
    base_col     = selected_row["Base Column"]
    sort_attr    = selected_row["Sort Attribute"]
    description  = selected_row["Description"]
    required_col = selected_row["Required Column"]
    input_cols   = list(df_input.columns)

    sql_prompt = prompts.generate_single_table_sql_prompt(
        input_cols=input_cols,
        required_col=required_col,
        description=description,
        base_col=base_col
    )

    print_rule("Calling LLM for sort SQL")
    sql = call_gpt(sql_prompt).strip()
    if not sql:
        raise RuntimeError("LLM returned empty SQL.")
    print_rule("🧾 Generated SQL")
    print(sql, "\n")

    result_df = con.execute(sql).df()
    return result_df

def generate_augmented_sql_and_run(con,
                                   df_input: pd.DataFrame,
                                   data_lake: dict[str, pd.DataFrame],
                                   augment_data: dict) -> tuple[str, pd.DataFrame]:
    datalake_table_name = augment_data["matched_table"]
    input_table_key     = augment_data["join_key_input"]
    datalake_table_key  = augment_data["join_key_datalake"]
    sort_by_column      = augment_data["matched_column"]

    prompt = prompts.generate_augmented_sql_prompt(
        input_cols=df_input.columns,
        datalake_table_name=datalake_table_name,
        join_key_input=input_table_key,
        join_key_datalake=datalake_table_key,
        sort_cols=[sort_by_column]
    )

    # print_rule("Calling LLM for augmented SQL")
    # sql = call_gpt(prompt).strip()
    # if not sql:
    #     raise RuntimeError("LLM returned empty augmented SQL.")
    sql = prompts.build_augmented_sql(datalake_table_name=datalake_table_name, join_key_input=input_table_key, join_key_datalake=datalake_table_key, sort_cols=[sort_by_column])

    print_rule("🧾 Generated Augmented SQL")
    print(sql, "\n")

    # Register the datalake table in DuckDB under its table name
    typed_df, inferred = infer_type.infer_and_cast_df(data_lake[datalake_table_name], percent_scale=True)
    con.register(datalake_table_name, typed_df)
    # con.register(datalake_table_name, data_lake[datalake_table_name])

    out_df = con.execute(sql).df()
    return sql, out_df

# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="InsightSort (CLI) — discover interesting sort attributes and optionally augment data from a data-lake."
    )
    parser.add_argument("--datalakes-root", default="datalakes", help="Root folder containing data-lakes (default: %(default)s)")
    parser.add_argument("--lake", help="Name of the data-lake to use (folder under datalakes-root). If omitted, you'll be prompted.")
    parser.add_argument("--input-table", help="Stem name of input CSV (under <lake>/input_tables). If omitted, you'll be prompted.")
    parser.add_argument("--export", help="Path to save the final output CSV (optional).")
    parser.add_argument("--print-json", action="store_true", help="Print the chosen suggestion record as JSON before running SQL.")
    args = parser.parse_args()

    datalakes_root = Path(args.datalakes_root)
    if not datalakes_root.exists():
        eprint(f"❌ Datalakes root not found: {datalakes_root}")
        sys.exit(1)

    # Pick data-lake
    available = list_dir_names(datalakes_root)
    if not available:
        eprint(f"❌ No data-lakes found under {datalakes_root}")
        sys.exit(1)

    if args.lake and args.lake in available:
        lake_name = args.lake
    else:
        if args.lake and args.lake not in available:
            eprint(f"⚠️ Requested lake '{args.lake}' not found; choose interactively.")
        lake_name = choose_from_list("Select a data-lake:", available)

    lake_dir   = datalakes_root / lake_name
    index_dir  = lake_dir / "index_files"

    print_rule(f"Loading data-lake '{lake_name}'")
    data_lake = load_datalake_tables(lake_dir)
    print(f"Loaded {len(data_lake)} tables from {lake_dir/'all_tables'}.")

    print_rule("Ensuring indexes")
    ensure_indexes(data_lake, index_dir)
    print("✅ Indexes present.")

    # Connect DuckDB; register 'input_table' later
    con = duckdb.connect()

    # Select & load input table
    try:
        input_name, df_input, input_path = select_input_table(lake_dir, prefer=args.input_table)
    except Exception as e:
        eprint(f"❌ {e}")
        sys.exit(1)

    # print_rule(f"Input table: {input_name}")
    # print_df(df_input)

    # Register the input table in DuckDB
    con.unregister("input_table") if "input_table" in con.execute("SHOW TABLES").df().values else None
    con.register("input_table", df_input)

    table_descriptions = table_description_builder.load_table_descriptions(index_dir)

    # Generate suggestions

    start_time = time.time()
    input_table_minhash = minhash_builder.build_minhashes(datalake={'input_table': df_input}, parallel_enabled=False)['input_table']
    all_minhashes = minhash_builder.load_minhashes(index_dir)

    suggestions_df, augmentation_cache = generate_suggestions(df_input, input_table_minhash, all_minhashes, data_lake, index_dir, table_descriptions)
    end_time = time.time()
    print(f"generate_suggestions runtime: {end_time - start_time:.2f} seconds")

    # Display & pick
    while True:
        _, selected_row, semantic_util = show_suggestions_and_pick(df_input, suggestions_df)

        if args.print_json:
            print_rule("Selected suggestion (JSON)")
            print(json.dumps(selected_row.to_dict(), indent=2))

        column_present = (selected_row.get("Column present", "No") == "Yes")

        try:
            if column_present:
                if yes_no("\nRequired column is present. Generate and run sort SQL now?"):
                    result_df = generate_sort_sql_and_run(con, df_input, selected_row)
                    print_rule("Result (sorted table)")
                    print_df(result_df)
                    if args.export or yes_no("Export result to CSV?", default_yes=False):
                        out = Path(args.export) if args.export else Path.cwd() / f"{input_name}__sorted.csv"
                        export_df(result_df, out)
                else:
                    print("Skipped SQL generation.")
            else:
                print_rule("Augmentation suggested (required column missing)")
                base_col  = selected_row["Base Column"]
                sort_attr = selected_row["Sort Attribute"]
                aug = augmentation_cache.get((base_col, sort_attr))
                if not aug:
                    raise RuntimeError("Could not find a viable augmentation for the selected suggestion.")

                print("Suggested Attribute:     ", aug["suggested_attribute"])
                print("Matched Table / Column:  ", aug["matched_table"], "/", aug["matched_column"])
                print("Join Keys (input ↔ lake):", aug["join_key_input"], "<->", aug["join_key_datalake"])
                print(f"Semantic Distance:       {float(aug['semantic_distance']):.4f}")
                print(f"Join Distance:           {float(aug['join_distance']):.4f}")

                if yes_no("\nApply augmentation and run augmented SQL?"):
                    sql, out_df = generate_augmented_sql_and_run(con, df_input, data_lake, aug)
                    print_rule("Augmented result")
                    default_max_rows = 100
                    print(f"Showing up to {default_max_rows} rows as a sample.")
                    print_df(out_df, max_rows=default_max_rows)
                    if len(out_df) > default_max_rows:
                        show_all = yes_no(f"Show all {len(out_df)} rows?", default_yes=False)
                        if show_all:
                            print_df(out_df, max_rows=len(out_df))
                    if args.export or yes_no("Export augmented result to CSV?", default_yes=False):
                        out = Path(args.export) if args.export else Path.cwd() / f"{input_name}__augmented_sorted.csv"
                        export_df(out_df, out)
                else:
                    print("Skipped augmentation.")
        except Exception as e:
            eprint("\n❌ Error during SQL generation/execution:")
            eprint(e)
            eprint(traceback.format_exc())
            sys.exit(2)

        print_rule("Done")

if __name__ == "__main__":
    main()
