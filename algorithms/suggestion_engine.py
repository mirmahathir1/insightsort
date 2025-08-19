"""
Utilities to filter numeric-like columns from a data lake of pandas DataFrames.

Rule: For each column, take up to the first 20 non-null values, convert to
strings, and if any value contains alphabetical letters (A-Z/a-z), discard the
column. Otherwise, keep it as numeric-like.
"""

from __future__ import annotations

import re
from typing import Dict, List, Mapping
import pprint
import pandas as pd
import llm_utils
from algorithms import join_discovery
from algorithms import semantic_type_extractor
from algorithms import table_description_builder
from algorithms import prompts
import embedding_utils
import helpers
from tqdm import tqdm
import json
from pathlib import Path
from difflib import SequenceMatcher
from algorithms import index_builder
import sql_cache
from algorithms import sql_gen
from algorithms import infer_type
from data_path import data_path


_HAS_ALPHA_RE = re.compile(r"[A-Za-z]")


def _is_numeric_like(series: pd.Series, sample_size: int = 100) -> bool:
	"""Return True if the column appears numeric-like per the letter rule.

	- Inspect up to the first `sample_size` non-null values.
	- Convert to string and check if any contain alphabetic letters.
	- If any contain letters, it's NOT numeric-like.

	Empty columns (no non-null samples) are treated as non-numeric.
	"""

	# Get up to `sample_size` non-null values
	# Use head before astype to avoid converting the entire column to string
	# Replace with the most occurring top 20 values
	non_null_sample = series.dropna().value_counts().head(sample_size).index
	non_null_sample = series.dropna().head(sample_size)
	if non_null_sample.empty:
		return False

	for val in non_null_sample.astype(str):
		if _HAS_ALPHA_RE.search(val):
			return False
	return True


def get_numeric_columns_by_table(
	data_lake: Mapping[str, pd.DataFrame], sample_size: int = 20
) -> Dict[str, List[str]]:
	"""Return mapping of table name -> list of numeric-like column names.

	Args:
		data_lake: Mapping where key is table name and value is a pandas DataFrame.
		sample_size: Number of non-null samples to check per column (default 20).

	Returns:
		Dict mapping each table name to a list of columns that pass the
		alphabetic-letter exclusion rule.
	"""

	result: Dict[str, List[str]] = {}
	for table_name, df in data_lake.items():
		numeric_cols: List[str] = []
		for col in df.columns:
			if _is_numeric_like(df[col], sample_size=sample_size):
				numeric_cols.append(col)

		result[table_name] = numeric_cols

	return result

def get_interesting_columns_by_table(
		input_table: pd.DataFrame,
		input_table_semantic_types: dict[str, str],
		all_datalake: Mapping[str, pd.DataFrame],
		joinable_tables: List[str],
		table_descriptions: Mapping[str, str],
		all_semantic_types: dict[str, Mapping[str, str]],
		only_numeric_columns: dict[str, List[str]]
	):

	input_table_string = ""
	data_lake_string = ""

	datalake_column_id = 0

	input_table_string += "Input Table:\n\n"
	for col in input_table.columns:
		input_table_string += f"column name: {col}, semantic type: {input_table_semantic_types[col]}\n"
		input_table_string += f"sample: {input_table[col].dropna().astype(str).head(5).tolist()}\n"

	id_to_column_mapping = {}

	for table in joinable_tables:
		dataframe = all_datalake[table]
		if len(only_numeric_columns[table]) == 0:
			continue  # Skip tables with no numeric columns
		table_string = f"Table Name: {table}:\n"
		table_string += f"Description: {table_descriptions[table]}\n"
		
		for col in only_numeric_columns[table]:
			id_to_column_mapping[f"{datalake_column_id}"] = (table, col)
			table_string += f"column id: {datalake_column_id}, column name: {all_semantic_types[table][col]}\n"
			table_string += f"column sample: {dataframe[col].dropna().astype(str).head(5).tolist()}\n"

			datalake_column_id += 1

		table_string += "\n"
		data_lake_string += table_string
	prompt = f"""
You are a smart data assistant. A user has uploaded a table with the following columns:

{input_table_string}

Here are the columns of tables from a data lake that can be used for semantic sorting:

{data_lake_string}

Your task is to analyze the data lake columns and suggest **semantic sorting options** to the input table.

### Instructions:
For each column in the datalake-
1. Check if it can be used for semantic sorting of the input table if it was joined with the input table.
2. Identify which input column can benefit if the data lake column is used to **semantically sort** the input table. Use only the columns which are meaningful for semantic interpretation.
3. Give an interestingness score between 0 and 1 for each data lake column based on how semantically insightful it is for sorting the input table.
4. Every data lake column should be evaluated. If the column is not useful for sorting, give it a score of 0.
5. For each data lake column, provide:
   - `base_column`: The column from the input table.
   - `datalake_column_name`: The data lake column name.
   - `description`: What insight the user gains from this sort.
   - `interestingness`: A number between 0 and 1 estimating how insightful this sort might be.

The interestingness score should be based on the following criteria:
1. The score should be high if the column provides a **meaningful semantic insight** into the data associated with the base_column.
2. The score should be high if the new column provide meaningful insights.
3. Data lake columns such as IDs, codes or other semantically uninformative columns should have a low score.

Respond ONLY and ONLY in the following JSON format (don't include backticks or markdown tags) e.g., don't wrap the response inside ```json```:

{{
	"<datalake_column_id>": {{
		"base_column": "column_name_from_input_table",
		"datalake_column_name": "...",
		"description": "Brief description of the insight gained from this column",
		"interestingness": <float>,  # Example score between 0 and 1
	}},
	"<datalake_column_id2>": {{
		"base_column": "another_column_name_from_input_table",
		"datalake_column_name": "...",
		"description": "Brief description of the insight gained from this column",
		"interestingness": <float>,  # Example score between 0 and 1
	}},
	...
}}
""".strip()
	
	print(prompt)
	# exit(0)

	response = llm_utils.call_gpt(prompt=prompt)
	# Parse the response

	suggestions = llm_utils.extract_json_object(response)

	pprint.pprint(suggestions)

	final_suggestions: dict[str, dict[str, float]] = {}

	for key, suggestion in suggestions.items():
		(table_name, column_name) = id_to_column_mapping[key]
		base_column = suggestion["base_column"]
		datalake_column_name = column_name
		description = suggestion["description"]
		interestingness = suggestion["interestingness"]

		if base_column not in final_suggestions:
			final_suggestions[base_column] = []

		final_suggestions[base_column].append({
			"column": datalake_column_name,
			"table": table_name,
			"description": description,
			"interestingness": interestingness
		})

	return final_suggestions

def generate_numeric_column_suggestions(
        input_table: pd.DataFrame,
        input_table_minhash, 
        all_minhashes, 
        data_lake: dict[str, pd.DataFrame], 
        table_descriptions: dict[str, str],
        cosine_distance_threshold_for_existing_column_mapping,
        suggestion_deduplication_semantic_type_distance_threshold,
        semantic_types,
        semantic_type_embeddings: dict[str, dict[str, list[float]]],
		min_joinability_distance_threshold
        ) -> tuple[pd.DataFrame, dict]:
    """
    Calls LLM to generate suggestions, filters/augments where needed,
    enriches with semantic scores; returns (suggestions_df, augmentation_cache)
    """
    input_table_semantic_types = semantic_type_extractor.infer_semantic_types_for_df(df=input_table)

    joinable_tables = table_description_builder.table_filter_using_minhash(
        input_table_minhash=input_table_minhash,
        table_minhashes=all_minhashes,
        minhash_jaccard_threshold= 1 - min_joinability_distance_threshold
    )

    only_numeric_columns = get_numeric_columns_by_table(
        data_lake=data_lake,
        sample_size=20
    )

    joinable_table_segments = helpers.split_list(joinable_tables, 10)

    all_suggestions = {}
    helpers.print_rule("Calling LLM for suggestions")
    for single_segment_of_joinable_tables in tqdm(joinable_table_segments):
        print("single_segment_of_joinable_tables")
        print(single_segment_of_joinable_tables)
        table_segment_suggestions = get_interesting_columns_by_table(
            	input_table= input_table,
                input_table_semantic_types= input_table_semantic_types,
                all_datalake= data_lake,
                joinable_tables= single_segment_of_joinable_tables,
                table_descriptions= table_descriptions,
                all_semantic_types= semantic_types,
                only_numeric_columns= only_numeric_columns
            )
        for base_col, suggestions in table_segment_suggestions.items():
            if base_col not in all_suggestions:
                all_suggestions[base_col] = []
            all_suggestions[base_col].extend(suggestions)

    with open(data_path() / "all_suggestions.json", "w", encoding="utf-8") as f:
        json.dump(all_suggestions, f, indent=4, ensure_ascii=False)
    print("✅ Dumped all suggestions to all_suggestions.json")

    augmentation_cache = {}
    rows = []

    helpers.print_rule("Evaluating suggestions against the data lake")
    input_table_semantic_type_embeddings = semantic_type_extractor.build_semantic_type_embeddings(input_table)
    print("discover_augmentable_column")
    for base_col, sort_list in all_suggestions.items():
        for s in sort_list:
            aug = join_discovery.discover_join(
                datalake_table= s["table"],
                datalake_column= s["column"],
                input_table_minhash=input_table_minhash,
                input_table_semantic_type_embeddings=input_table_semantic_type_embeddings,
                semantic_types=semantic_types,
                minhashes=all_minhashes,
                base_col=base_col,
                min_joinability_distance_threshold=min_joinability_distance_threshold,
                cosine_distance_threshold_for_existing_column_mapping=cosine_distance_threshold_for_existing_column_mapping
            )
            if aug is None:
                # skip suggestions that can't be satisfied
                continue
            aug['interestingness'] = s['interestingness']
            aug['description'] = s['description']
            aug['base_column'] = base_col
            aug['Augmented Column'] = semantic_types[s['table']][s['column']]
            aug['Source Table'] = s['table']
            augmentation_cache[(base_col, aug["datalake_table"], aug["datalake_column"])] = aug

            rows.append(aug)

    if len(rows) == 0:
        raise RuntimeError("No viable suggestions after augmentation checks.")

    suggestions_df = pd.DataFrame(rows)

    suggestions_df = suggestions_df.sort_values(by="interestingness", ascending=False).drop_duplicates(subset=["datalake_table", "datalake_column"]).reset_index(drop=True)

    kept_indices = []
    kept_embs = []  # list[np.ndarray]
    for idx, row in suggestions_df.iterrows():
        emb = semantic_type_embeddings[row['datalake_table']][row['datalake_column']]
        if len(kept_embs) == 0:
            kept_indices.append(idx)
            kept_embs.append(emb)
            continue

        is_too_close = False
        for previous_emb in kept_embs:
            if embedding_utils._cosine_distance(emb, previous_emb) < suggestion_deduplication_semantic_type_distance_threshold:
                is_too_close = True
                break
        if is_too_close:
            continue  # skip this row, it's too close to a previous one

        kept_indices.append(idx)
        kept_embs.append(emb)

    suggestions_df = suggestions_df.loc[kept_indices].reset_index(drop=True)

    return suggestions_df, augmentation_cache

def generate_suggestions(
        input_table: pd.DataFrame, 
        input_table_minhash, 
        all_minhashes, 
        data_lake: dict[str, pd.DataFrame], 
        index_dir: Path, 
        table_descriptions: list[dict[str, str]],
        semantic_distance_threshold_for_datalake_column_mapping,
        cosine_distance_threshold_for_existing_column_mapping,
        min_joinability_distance_threshold,
        semantic_types
        ) -> tuple[pd.DataFrame, dict]:
    """
    Calls LLM to generate suggestions, filters/augments where needed,
    enriches with semantic scores; returns (suggestions_df, augmentation_cache)
    """
    column_names = list(input_table.columns)

    input_table_semantic_types = semantic_type_extractor.infer_semantic_types_for_df(df=input_table)

    joinable_tables = table_description_builder.table_filter_using_minhash(
        input_table_minhash=input_table_minhash,
        table_minhashes=all_minhashes,
        minhash_jaccard_threshold= 1 - min_joinability_distance_threshold
    )

    joinable_table_descriptions = {table: table_descriptions[table] for table in joinable_tables if table in table_descriptions}

    table_description_segments = helpers.split_dict(joinable_table_descriptions, 20)

    all_suggestions = {}
    helpers.print_rule("Calling LLM for suggestions")
    for segment in tqdm(table_description_segments):
        prompt = prompts.build_suggestion_prompt(input_table, column_names, other_table_descriptions=segment)

        gpt_response = llm_utils.call_gpt(prompt)
        table_description_segment_suggestions = llm_utils.parse_suggestion(gpt_response)
        for base_col, suggestions in table_description_segment_suggestions.items():
            if base_col not in all_suggestions:
                all_suggestions[base_col] = []
            all_suggestions[base_col].extend(suggestions)

    # Dump all suggestions as .json with indent=4 in file
    with open(data_path() / "all_suggestions.json", "w", encoding="utf-8") as f:
        json.dump(all_suggestions, f, indent=4, ensure_ascii=False)
    print("✅ Dumped all suggestions to all_suggestions.json")

    SIMILARITY_THRESHOLD = 0.92  # adjust as needed

    for base_col, suggestions in all_suggestions.items():
        unique_suggestions = []
        seen = []
        for s in suggestions:
            sort_attr = s["column"]
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

    # Load indexes once
    semantic_types, semantic_type_hnsw_index, all_minhashes, all_table_descriptions = index_builder.load_indexes(index_dir)

    augmentation_cache = {}
    rows = []

    # suggestions: { base_col: [ {column, description, interestingness, "column present in the table": "Yes"/"No"} ] }
    helpers.print_rule("Evaluating suggestions against the data lake")
    input_table_semantic_type_embeddings = semantic_type_extractor.build_semantic_type_embeddings(input_table)
    print("discover_augmentable_column")
    for base_col, sort_list in all_suggestions.items():
        for s in sort_list:
            # print(f"Evaluating suggestion for base column '{base_col}'")
            # print(f"  Sort Attribute: {sort_attr}")
            col_present = (s["column present in the table"] == "Yes")
            sort_attr = s["column"]
            if not col_present:
                aug = join_discovery.discover_augmentable_column(
                    suggested_attribute=sort_attr,
                    input_table=input_table,                                  # input table
                    input_table_minhash=input_table_minhash,
                    input_table_semantic_type_embeddings=input_table_semantic_type_embeddings,
                    datalake=data_lake,
                    semantic_types=semantic_types,
                    minhashes=all_minhashes,
                    semantic_type_hnsw_index=semantic_type_hnsw_index,
                    base_col=base_col,
                    top_k=5,
                    min_joinability_distance_threshold=min_joinability_distance_threshold,
                    semantic_distance_threshold_for_datalake_column_mapping=semantic_distance_threshold_for_datalake_column_mapping,
                    cosine_distance_threshold_for_existing_column_mapping=cosine_distance_threshold_for_existing_column_mapping
                )
                if aug is None:
                    # skip suggestions that can't be satisfied
                    continue
                augmentation_cache[(base_col, sort_attr)] = aug

            rows.append({
                "Base Column":     base_col,
                "Sort Attribute": s["column"],
                "Sort Attribute Name":  s["name"],
                "Description":     s["description"],
                "Interestingness": s["interestingness"],
                "Column present":  "Yes" if col_present else "No",
                "Matched Column": sort_attr if col_present else aug['matched_column'],
                "Matched Table":   "input_table" if col_present else aug['matched_table'],
            })


    if len(rows) == 0:
        raise RuntimeError("No viable suggestions after augmentation checks.")

    suggestions_df = pd.DataFrame(rows)

    # Sort suggestions_df by Interestingness in descending order
    suggestions_df = suggestions_df.sort_values(by="Interestingness", ascending=False).drop_duplicates(subset=["Matched Table", "Matched Column"]).reset_index(drop=True)

    print("update_suggestions_with_semantic_scores")
    # suggestions_df = update_suggestions_with_semantic_scores(suggestions_df, input_cols)
    suggestions_df = prompts.update_suggestions_with_interestingness_score(
        suggestions_df=suggestions_df, input_df=input_table, input_df_semantic_types=input_table_semantic_types, all_semantic_types=semantic_types, data_lake=data_lake)
    suggestions_df.index = suggestions_df.index + 1  # 1-based display
    return suggestions_df, augmentation_cache


def generate_augmented_sql_and_run(con,
                                   df_input: pd.DataFrame,
                                   data_lake: dict[str, pd.DataFrame],
                                   augment_data: dict,
                                   cached: bool = False) -> tuple[str, pd.DataFrame]:
    """
    Build and run augmented SQL joining input_table with a datalake table based on augment_data.
    Caching is delegated to with_augmented_sql_cache().
    """

    cache_result = sql_cache.read_augmented_sql_cache(augment_data=augment_data, cached=cached)

    if cache_result is not None:
        sql, out_df = cache_result
        helpers.print_rule("Using cached augmented SQL")
        return sql, out_df

    datalake_table_name = augment_data["datalake_table"]
    input_table_key     = augment_data["join_key_input"]
    datalake_table_key  = augment_data["join_key_datalake"]
    sort_by_column      = augment_data["datalake_column"]

    typed_df, _inferred = infer_type.infer_and_cast_df(
        data_lake[datalake_table_name], percent_scale=True
    )

    sql = sql_gen.build_augmented_sql(
        datalake_table_name=datalake_table_name,
        join_key_input=input_table_key,
        join_key_datalake=datalake_table_key,
        sort_cols=[sort_by_column],
        input_dataframe=df_input,
        datalake_dataframe=typed_df,
    )

    helpers.print_rule("🧾 Generated Augmented SQL")
    print(sql, "\n")

    # Register the datalake table in DuckDB under its table name
    con.register(datalake_table_name, typed_df)

    out_df = con.execute(sql).df()

    sql_cache.save_augmented_sql_cache(
        augment_data=augment_data,
        sql=sql,
        df=out_df,
        cached=cached
        )

    return sql, out_df