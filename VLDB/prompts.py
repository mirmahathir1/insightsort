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
2. For each such column, generate minimum of 5 (if rich with attributes) and up to 7 **interesting and diverse** sort options, based on real-world attributes (e.g., for column 'country': GDP, population, life expectancy, etc). Ignore alphabetical or simple value-based sorting.
3. Suggestions can involve **single or composite** attributes (e.g., "life expectancy + literacy rate").
4. For each suggestion, provide:
   - `column`: The **attribute name** used for sorting (e.g., GDP)
   - `description`: What insight the user gains from this sort
   - `interestingness`: A number between 0 and 1 estimating how insightful this sort might be
   - `required_column`: The column(s) needed for this sort (e.g., "gdp", "life_expectancy, literacy_rate")
   - `column present in the table`: "Yes" **only if** the required column(s) are present **and are usable directly with the base column** (i.e., sortable or groupable by it). Otherwise, say "No".

Respond ONLY and ONLY in the following JSON format (don't include backticks or markdown tags) e.g., don't wrap the response inside ```json```:

{{
  "country": [
    {{
      "column": "gdp",
      "description": "Sort by GDP to understand the economic output of each country. Higher GDP often correlates with higher living standards.",
      "required_column": "gdp (in trillions USD)",
      "column present in the table": "Yes"
    }},
    {{
      "column": "life expectancy + literacy rate",
      "description": "Sort by a composite view of human development using both life expectancy and literacy rate.",
      "required_column": "life_expectancy, literacy_rate",
      "column present in the table": "No"
    }}
  ],
  "region": [
    {{
      "column": "average gdp",
      "description": "Sort by average GDP per region to compare economic strength.",
      "required_column": "gdp (in trillions USD), region",
      "column present in the table": "No"
    }}
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

    
