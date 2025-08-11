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

# ── Your existing modules ─────────────────────────────────────────────────────
from algorithms.prompts import build_suggestion_prompt, generate_augmented_sql_prompt
from algorithms.llm_utils import call_gpt, parse_suggestion
from algorithms.index_builder import build_indexes_from_datalake, load_indexes
from algorithms.join_discovery import discover_augmentable_column
from algorithms.semantic_score import (
    compute_semantic_interestingness,
    update_suggestions_with_semantic_scores,
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def read_csv_safely(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except Exception as e:
        raise RuntimeError(f"Failed to read CSV: {path} — {e}")

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

def load_datalake_tables(lake_dir: Path) -> dict[str, pd.DataFrame]:
    """
    Reads all CSVs under lake_dir / 'all_tables' into DataFrames.
    Returns {table_name: dataframe}
    """
    all_tables_dir = lake_dir / "all_tables"
    tables = {}
    for csv_path in list_csv_files(all_tables_dir):
        try:
            tables[csv_path.stem] = read_csv_safely(csv_path)
        except Exception as e:
            eprint(f"⚠️  Skipping {csv_path.name}: {e}")
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

def generate_suggestions(df: pd.DataFrame, data_lake: dict[str, pd.DataFrame], index_dir: Path) -> tuple[pd.DataFrame, dict]:
    """
    Calls LLM to generate suggestions, filters/augments where needed,
    enriches with semantic scores; returns (suggestions_df, augmentation_cache)
    """
    sample_rows = df.head(5).to_dict(orient="records")
    column_names = list(df.columns)
    prompt = build_suggestion_prompt(sample_rows, column_names)

    print_rule("Calling LLM for suggestions")
    gpt_response = call_gpt(prompt)
    suggestions = parse_suggestion(gpt_response)
    if not suggestions:
        raise RuntimeError("Could not generate sorting suggestions.")

    # Load indexes once
    join_index, semantic_index, semantic_types, minhashes, semantic_type_hnsw_index = load_indexes(index_dir)

    augmentation_cache = {}
    rows = []

    # suggestions: { base_col: [ {column, description, interestingness, "column present in the table": "Yes"/"No"} ] }
    print_rule("Evaluating suggestions against the data lake")
    for base_col, sort_list in suggestions.items():
        for s in tqdm(sort_list):
            sort_attr   = s["column"]
            col_present = (s["column present in the table"] == "Yes")
            if not col_present:
                aug = discover_augmentable_column(
                    sort_attr,
                    df,                                  # input table
                    data_lake,
                    semantic_index,
                    join_index,
                    semantic_types,
                    minhashes,
                    semantic_type_hnsw_index,
                    base_col,
                    5
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
            })

    if not rows:
        raise RuntimeError("No viable suggestions after augmentation checks.")

    suggestions_df = pd.DataFrame(rows)
    input_cols = list(suggestions_df.columns)
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
    options = []
    for idx, row in sorted_df.iterrows():
        options.append(f"{row['Base Column']} ➝ {row['Sort Attribute']}  [#{idx}]")

    print("\nChoose a suggestion:")
    for i, text in enumerate(options, 1):
        print(f"  {i}. {text}")

    while True:
        raw = input("Enter choice number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            choice_num = int(raw)
            chosen_display = options[choice_num - 1]
            # extract original row index between [#idx]
            original_idx = int(chosen_display.split("[#")[-1].rstrip("]"))
            chosen_row = suggestions_df.loc[original_idx]
            return original_idx, chosen_row, semantic_util
        print("Invalid choice. Try again.")

def generate_sort_sql_and_run(con, df_input: pd.DataFrame, selected_row: pd.Series) -> pd.DataFrame:
    base_col     = selected_row["Base Column"]
    sort_attr    = selected_row["Sort Attribute"]
    description  = selected_row["Description"]
    required_col = selected_row["Required Column"]
    input_cols   = list(df_input.columns)

    sql_prompt = f"""
Given a table with the following columns: {input_cols}
Write an SQL query that sorts this table by {required_col} in descending order, assuming that column exists in the table and is aligned with {base_col}.

Here is what's exactly needed:
- The SQL query should sort the **entire table** according to this: {description}
- You may need to use GROUP BY, ORDER BY, OVER(), or any SQL techniques as needed.
- Ensure the final output includes **all original table columns plus any derived column** used in ORDER BY.
- Do not return a partial subset of the table — return a **fully sorted version of the input table with the sorting column visible.**
- If any column name contains spaces or special characters, wrap it in **double quotes** (e.g., "gdp (in trillions USD)").
- Table name is 'input_table'

Return only the SQL query — no explanations or markdown formatting. Also don't include it in backticks.
""".strip()

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

    prompt = generate_augmented_sql_prompt(
        input_cols=df_input.columns,
        datalake_table_name=datalake_table_name,
        join_key_input=input_table_key,
        join_key_datalake=datalake_table_key,
        sort_col=sort_by_column
    )

    print_rule("Calling LLM for augmented SQL")
    sql = call_gpt(prompt).strip()
    if not sql:
        raise RuntimeError("LLM returned empty augmented SQL.")
    print_rule("🧾 Generated Augmented SQL")
    print(sql, "\n")

    # Register the datalake table in DuckDB under its table name
    con.register(datalake_table_name, data_lake[datalake_table_name])
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

    print_rule(f"Input table: {input_name}")
    print_df(df_input)

    # Register the input table in DuckDB
    con.unregister("input_table") if "input_table" in con.execute("SHOW TABLES").df().values else None
    con.register("input_table", df_input)

    # Generate suggestions
    suggestions_df, augmentation_cache = generate_suggestions(df_input, data_lake, index_dir)

    # Display & pick
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
                print_df(out_df)
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
