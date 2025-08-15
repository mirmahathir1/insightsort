def build_suggestion_prompt(input_table, column_names, other_table_descriptions):
    # Get the most frequent 5 values for each column in input_table
    input_table_string = ""
    for col in column_names:
        most_frequent_values = input_table[col].dropna().value_counts().head(5).index.tolist()
        
        input_table_string += f"column {col}: {', '.join(map(str, most_frequent_values))}\n"

    other_table_descriptions_string = ""
    for table_name, description in other_table_descriptions.items():
        other_table_descriptions_string += f"{table_name}: {description}\n"

    return f"""
You are a smart data assistant. A user has uploaded a table with the following columns:

{column_names}

Here are the columns of the uploaded table with a sample of values:
{input_table_string}

Your task is to analyze this table and suggest **semantic sorting options**.

### Instructions:
1. Identify which columns can be used to **semantically sort** the table (e.g., country, region, job_levels, company, etc). Use only the columns which are meaningful for semantic interpretation.
2. For each such input column (base column), generate **interesting and diverse** sort options, based on real-world attributes (e.g., for column 'country': GDP, population, life expectancy, etc). Ignore alphabetical or simple value-based sorting.
3. The suggestions must come from the tables provided in the `other_table_descriptions` section, which contains attributes that can be used for sorting.
4. For each suggestion, provide:
   - `column`: The single **attribute name** used for sorting that may or may not be present in the input table.
   - `name`: The name of the column in natural language. It should not follow any variable naming conventions (e.g., no underscores, camelCase, etc). Use natural language names.
   - `table`: The name of the table from which this attribute comes (e.g., "world_data", "company_info", etc).
   - `description`: What insight the user gains from this sort
   - `interestingness`: A number between 0 and 1 estimating how insightful this sort might be
   - `column present in the table`: "Yes" **only if** `column` is present in the input table. Otherwise, say "No".
5. Do not add sorting options that represent boolean status, codes of entities, dates, or other non-semantic attributes. The sorting options should be rich in attributes that provide meaningful insights.
6. You may only add categorical columns as sorting options where the values have a **natural order** (e.g., "low", "medium", "high").
7. You may add numerical sorting options where the values are **meaningful** (e.g., "GDP", "population", "cost of living index").

Respond ONLY and ONLY in the following JSON format (don't include backticks or markdown tags) e.g., don't wrap the response inside ```json```:

{{
  "(base_column_1)": [
    {{
      "column": "...",
      "name": "...",
      "table": "...",
      "description": "...",
      "interestingness": 0.0-1.0,
      "column present in the table": "Yes"/"No"
    }},
    {{
      "column": "...",
      "name": "...",
      "table": "...",
      "description": "...",
      "interestingness": 0.0-1.0,
      "column present in the table": "Yes"/"No"
    }},
  ],
  "(base_column_2)": [
    {{
      "column": "...",
      "name": "...",
      "table": "...",
      "description": "...",
      "interestingness": 0.0-1.0,
      "column present in the table": "Yes"/"No"
    }},
  ]
}}

Only include columns that are **meaningful to semantically sort**. Do not make up data that contradicts the sample rows. The goal is to suggest intelligent, real-world-based ways to sort the table.

`other_table_descriptions`:

{other_table_descriptions_string}

"""


def compute_semantic_utility_prompt(input_columns: list[str], candidate_columns: list[str]) -> str:
    return f"""
You are a data expert evaluating how meaningful it is to sort a dataset.

The table contains the following columns:
{', '.join(input_columns)}

You are considering sorting this table using the following attribute(s):
{', '.join(candidate_columns)}

Please rate the usefulness of sorting the table using these attributes, based on:
- Whether the sort helps users compare, explore, or analyze the data better
- Whether the sort adds new perspective or insight (not already captured by existing columns)
- Whether the attributes are generally valuable for understanding or prioritizing rows

Score from 0 to 1:
- 1 means "extremely useful and insightful"
- 0 means "not useful or redundant"

Return only a decimal number between 0 and 1, without explanation.
"""



# def generate_augmented_sql_prompt(input_cols, datalake_table_name, join_key_input, join_key_datalake, sort_col):
#     return f"""
# You are given:
# - An input table named `input_table` with the following columns: {input_cols}
# - A data lake table named `{datalake_table_name}`

# Your task is to:
# 1. Perform an inner join between `input_table` and `{datalake_table_name}` using:
#    - `input_table.{join_key_input}` = `{datalake_table_name}.{join_key_datalake}`
# 2. Return all columns from `input_table`, and the column `{sort_col}` from `{datalake_table_name}`
# 3. Sort the final result in descending order based on `{datalake_table_name}.{sort_col}`
# 4. Ensure all column references in the SELECT, JOIN, and ORDER BY clauses are fully qualified using table names
# 5. Wrap column names that contain spaces or special characters in double quotes, e.g., "cost of living index"

# Output only the SQL query — no explanations, no markdown, and no extra formatting.
# """    

# def generate_augmented_sql_prompt(input_cols, datalake_table_name, join_key_input, join_key_datalake, sort_cols):
#     """
#     sort_cols can be a single column name (str) or a list/tuple of column names.
#     """
#     if isinstance(sort_cols, (list, tuple)):
#         sort_cols_text = ", ".join(sort_cols)
#     else:
#         sort_cols_text = str(sort_cols)

#     return f"""
# You are given:
# - An input table named `input_table` with the following columns: {input_cols}
# - A data lake table named `{datalake_table_name}`

# Your task is to:
# 1. Perform an INNER JOIN between `input_table` and `{datalake_table_name}` using:
#    - `input_table.{join_key_input}` = `{datalake_table_name}.{join_key_datalake}`
# 2. Return ONLY the following columns:
#    - `input_table.{join_key_input}`
#    - `{datalake_table_name}.{join_key_datalake}`
#    - `{datalake_table_name}.{sort_cols_text}`  (if multiple, include all of them)
# 3. Discard duplicate rows by using SELECT DISTINCT over the projected columns.
# 4. Sort the final result in descending order by `{datalake_table_name}.{sort_cols_text}`.
#    - If multiple sort attributes are provided, sort by them in the given order, all DESC.
# 5. Ensure all column references in SELECT, JOIN, and ORDER BY clauses are fully qualified with table names.
# 6. Wrap column names that contain spaces or special characters in double quotes, e.g., "cost of living index".

# Output only the SQL query — no explanations, no markdown, no extra formatting and no ```sql annotation.
# """

# def generate_augmented_sql_prompt(input_cols, datalake_table_name, join_key_input, join_key_datalake, sort_cols):
#     """
#     sort_cols can be a single column name (str) or a list/tuple of column names.
#     """
#     if isinstance(sort_cols, (list, tuple)):
#         sort_cols_text = ", ".join(sort_cols)
#     else:
#         sort_cols_text = str(sort_cols)

#     return f"""
# You are given:
# - An input table named `input_table` with the following columns: {input_cols}
# - A data lake table named `{datalake_table_name}`

# Your task is to:
# 1. Perform an INNER JOIN between `input_table` and `{datalake_table_name}` using:
#    - `input_table.{join_key_input}` = `{datalake_table_name}.{join_key_datalake}`
# 2. Return ONLY the following columns:
#    - `input_table.{join_key_input}`
#    - `{datalake_table_name}.{sort_cols_text}`  (if multiple, include all of them)
# 3. Discard duplicate rows by using SELECT DISTINCT over the projected columns.
# 4. Sort the final result in descending order by `{datalake_table_name}.{sort_cols_text}`.
#    - If multiple sort attributes are provided, sort by them in the given order, all DESC.
# 5. Ensure all column references in SELECT, JOIN, and ORDER BY clauses are fully qualified with table names.
# 6. Wrap column names that contain spaces or special characters in double quotes, e.g., "cost of living index".

# Output only the SQL query — no explanations, no markdown, no extra formatting and no ```sql annotation.
# """



def generate_single_table_sql_prompt(input_cols, required_col, description, base_col):
    return f"""
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

import pandas as pd

def generate_semantic_type_prompt(df: pd.DataFrame, top_k: int = 20) -> str:
    """
    Build a prompt for OpenAI ChatCompletion that asks the model to
    infer a high-level semantic type for each DataFrame column.

    Parameters
    ----------
    df : pd.DataFrame
        The input data whose columns need semantic typing.
    top_k : int, default 20
        Number of most-frequent (non-null) values to show per column.

    Returns
    -------
    str
        A ready-to-use prompt string.
    """
    header = (
        "You are a semantic-typing assistant.\n"
        "For each column below, infer an elaborate semantic_type "
        "e.g. detailed elaborate name (without any underscores, put necessary spaces and no camel case).\n"
        f"Base your decision **only** on the top {top_k} most-frequent values provided.\n"
        "Return your answer as a single JSON object whose keys are the column names "
        "and whose values are the chosen semantic_type strings. "
        "Output **nothing** except this JSON (don't include backticks or markdown tags) e.g., don't wrap the response inside ```json```"
    )

    lines = [header, ""]

    for col in df.columns:
        # Grab top-k frequent non-null values (as strings to avoid JSON issues)
        top_vals = (
            df[col]
            .dropna()
            .astype(str)
            .value_counts()
            .head(top_k)
            .index
            .tolist()
        )
        # Escape any double-quotes to keep the prompt valid
        escaped = [v.replace('"', r"\"") for v in top_vals]
        example_block = ", ".join(f'"{v}"' for v in escaped)
        lines.append(f'{col} = [{example_block}]')

    return "\n".join(lines)

import math
import json
import pandas as pd


def build_table_description_prompt(
    df: pd.DataFrame,
    table_name: str,
    *,
    top_k: int = 3,
    max_value_len: int = 40,
) -> str:
    """
    Return a triple-quoted prompt string for ChatGPT to generate a single-line description of a table.
    """

    def _safe_str(x) -> str:
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return ""
        s = str(x).replace("\n", " ").replace("\r", " ").strip()
        return (s[: max_value_len - 1] + "…") if len(s) > max_value_len else s

    preview: dict[str, list[str]] = {}
    for col in df.columns:
        ser_str = df[col].dropna().astype(str)
        if ser_str.empty:
            preview[col] = []
            continue
        top_vals = ser_str.value_counts().head(top_k).index.tolist()
        preview[col] = [_safe_str(v) for v in top_vals]

    preview_block = json.dumps(
        {
            "table_name": table_name,
            "columns": list(df.columns),
            "top_values_per_column": preview,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return f"""
You are given metadata about a database table and some sample values. 
Write a concise, single-sentence description of what this table represents and the kind of data it contains. 
Focus on meaning, not internal pipeline details. 
Avoid listing every column; summarize the table's purpose and typical content in one line.

TABLE CONTEXT (JSON): {preview_block}

Output format (strict JSON):
{{
  "table": "{table_name}",
  "description": "<one-line description>"
}}

Requirements:
- The JSON must be valid and on its own (no extra text before/after).
- "description" must be a single line (no newlines), <= 200 characters if possible.
- Do NOT invent columns that are not present; use the provided context.
"""
