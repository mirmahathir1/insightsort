def build_suggestion_prompt(sample_rows, column_names):
    formatted_rows = "\n".join([str(row) for row in sample_rows])
    return f"""
You are a smart data assistant. A user has uploaded a table with the following columns:

{column_names}

Here are a few sample rows from the table:
{formatted_rows}

Your task is to analyze this table and suggest **semantic sorting options**.

### Instructions:
1. Identify which columns can be used to **semantically sort** the table (e.g., country, region, job_levels, company, etc). Use only the columns which are meaningful for semantic interpretation. Also, columns can be entities too, like companies, governments, schools, etc. 
2. For each such input column (base column), generate minimum of 5 (if rich with attributes) and up to 7 **interesting and diverse** sort options, based on real-world attributes (e.g., for column 'country': GDP, population, life expectancy, etc). Ignore alphabetical or simple value-based sorting.
3. For each suggestion, provide:
   - `column`: The single **attribute name** used for sorting that may or may not be present in the input table.
   - `description`: What insight the user gains from this sort
   - `interestingness`: A number between 0 and 1 estimating how insightful this sort might be
   - `column present in the table`: "Yes" **only if** `column` is present in the input table. Otherwise, say "No".

Respond ONLY and ONLY in the following JSON format (don't include backticks or markdown tags) e.g., don't wrap the response inside ```json```:

{{
  "(base_column_1)": [
    {{
      "column": "...",
      "description": "...",
      "column present in the table": "Yes"/"No"
    }},
    {{
      "column": "...",
      "description": "...",
      "column present in the table": "Yes"/"No"
    }},
  ],
  "(base_column_2)": [
    {{
      "column": "...",
      "description": "...",
      "column present in the table": "Yes"/"No"
    }},
  ]
}}

Only include columns that are **meaningful to semantically sort**. Do not make up data that contradicts the sample rows. The goal is to suggest intelligent, real-world-based ways to sort the table.
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



def generate_augmented_sql_prompt(input_cols, datalake_table_name, join_key_input, join_key_datalake, sort_col):
    return f"""
You are given:
- An input table named `input_table` with the following columns: {input_cols}
- A data lake table named `{datalake_table_name}`

Your task is to:
1. Perform an inner join between `input_table` and `{datalake_table_name}` using:
   - `input_table.{join_key_input}` = `{datalake_table_name}.{join_key_datalake}`
2. Return all columns from `input_table`, and the column `{sort_col}` from `{datalake_table_name}`
3. Sort the final result in descending order based on `{datalake_table_name}.{sort_col}`
4. Ensure all column references in the SELECT, JOIN, and ORDER BY clauses are fully qualified using table names
5. Wrap column names that contain spaces or special characters in double quotes, e.g., "cost of living index"

Output only the SQL query — no explanations, no markdown, and no extra formatting.
"""    

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
        "e.g. detailed elaborate name.\n"
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
