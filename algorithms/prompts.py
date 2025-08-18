import pandas as pd
import pprint
import helpers
import llm_utils

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

def update_suggestions_with_interestingness_score(suggestions_df: pd.DataFrame, input_df, input_df_semantic_types, all_semantic_types, data_lake) -> pd.DataFrame:
    """
    Re-score each suggestion's Interestingness using GPT, incorporating semantic-type context
    for input columns and (if applicable) matched data lake columns.

    Parameters
    ----------
    suggestions_df : pd.DataFrame
        Must contain columns: ["Base Column", "Sort Attribute", "Description", "Column present",
        "Matched Table", "Matched Column", "Interestingness"].
    input_df : pd.DataFrame
        The original input table.
    input_df_semantic_types : dict[str, str]
        Mapping of input_df column names to their semantic type strings.
    all_semantic_types : dict[str, dict[str, str]]
        Mapping of datalake table -> column -> semantic type.

    Returns
    -------
    pd.DataFrame
        The same dataframe with the "Interestingness" column replaced by GPT-assigned scores (floats).
    """

    input_columns_string = ""
    for idx, col in enumerate(input_df.columns):
        input_columns_string += f"Column name: {col}, description: {input_df_semantic_types[col]}\n"

    suggestions_string = ""
    for idx, row in suggestions_df.iterrows():
        base_col = row["Base Column"]
        sort_attr = row["Sort Attribute"]
        sort_attr_name = row["Sort Attribute Name"]
        matched_table = row["Matched Table"]
        matched_col = row["Matched Column"]
        col_present = row["Column present"]

        if matched_table == "input_table":
            examples = input_df[matched_col].dropna().unique()[:5]  # Get up to 5 examples
        else:
            examples = data_lake[matched_table][matched_col].dropna().unique()[:5]  # Get up to 5 examples

        if matched_table == "input_table":
            # If matched table is input_table, use its semantic type directly
            matched_sem_type = input_df_semantic_types[matched_col]
        else:
            matched_sem_type = all_semantic_types[str(matched_table)][str(matched_col)]

        suggestions_string += f"""
Suggestion ID: {idx + 1}
Suggestion By Human: {sort_attr_name}
Column present in input table: {col_present}
Best Match Column from the data lake: {matched_sem_type}
Best Match Value Examples: {examples}
"""

    prompt = f"""
You are a careful data assistant. A user has upload a table and the names of the columns are as below:

{input_columns_string}

You are also given a list of columns that are suggested by a human expert for sorting. These suggestions may or may not be in the input table. These suggestions are interesting ways to sort the input table.
Each suggestion has a best match column from a data lake, which is the closest match to the suggested column name. The best match column is either in the input table or in a seperate data lake table.
Ultimately, the best match column will be used to sort the input table after a join with the data lake table.

{suggestions_string}

Your task is to assign an interestingness score in [0,1] to each suggestion based on the following criteria:
- How semantically interesting it would be to sort using that attribute for this specific input table.
- Whether the matched data lake column closely matches the human given suggestion; better alignment => higher interestingness; poor alignment => lower interestingness.
- If the example values are categorical, it should be scored very low. Numeric values are more interesting for sorting.
- If the suggestion already matches a column in the input table but the suggestion is not present in the input table, it should be scored lower.
- The interestingness score across all suggestions should be normalized to [0, 1] range.
- For every suggestion, return an object with fields: "Suggestion Id", "Suggestion By Human", "Interestingness", "Reason of Score".
- Do not explain; output only a JSON array of objects.


Output format (strict JSON array):
[
  {{ "Suggestion Id": <string>, "Suggestion By Human": <string>, "Interestingness": <float>, "Reason of Score": <string> }},
]
"""
    
    print(prompt)
    helpers.print_df(suggestions_df.drop(columns=['Description']), max_rows=100)

    # Call GPT and parse JSON
    gpt_raw = llm_utils.call_gpt(prompt)
    
    payload = helpers.extract_json_object(gpt_raw)

    pprint.pprint(payload)

    # Map scores by id
    id_to_score = {}
    for obj in payload:
        rid = obj["Suggestion Id"]
        score = float(obj["Interestingness"])
        id_to_score[rid] = score

    pprint.pprint(id_to_score)

    for idx, row in suggestions_df.iterrows():
        suggestions_df.at[idx, "Interestingness"] = id_to_score[str(idx+1)]  # 1-based index in GPT response

    suggestions_df = suggestions_df.sort_values(by="Interestingness", ascending=False).reset_index(drop=True)

    return suggestions_df