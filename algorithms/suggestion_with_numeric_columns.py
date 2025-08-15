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
from algorithms import llm_utils

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
