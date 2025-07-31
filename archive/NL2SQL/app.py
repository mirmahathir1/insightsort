'''
This is the initial version of Semantic sorting using NL to SQL, where the openAI gives sql query (using some sorting order) to sort the table
'''



# import streamlit as st
# import sqlite3
# import pandas as pd
# import openai
# import re
# # from transformers import T5ForConditionalGeneration, T5Tokenizer


# # MODEL_NAME = "Salesforce/T5_large_nl2sql" 
# # tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME)
# # model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)

# openai.api_key = st.secrets["OPENAI_API_KEY"] 

# DB_PATH = "database.db"

# # Establish a Database Connection
# @st.cache_resource
# def get_connection():
#     return sqlite3.connect(DB_PATH, check_same_thread=False)

# conn = get_connection()

# # Fetch All Table Names in DB
# @st.cache_data
# def get_table_names():
#     query = "SELECT name FROM sqlite_master WHERE type='table';"
#     return pd.read_sql(query, conn)["name"].tolist()

# # Fetch Unique Column Values for Sorting 
# def get_unique_values(table_name, column_name):
#     try:
#         query = f"SELECT DISTINCT {column_name} FROM {table_name}"
#         unique_values = pd.read_sql(query, conn)[column_name].dropna().tolist()
#         return unique_values
#     except Exception:
#         return []

# # Function to Create Table if Not Exists
# def create_table_if_not_exists(table_name, df):
#     """Creates a new table if it does not exist in the database."""
#     try:
#         df.to_sql(table_name, conn, if_exists="fail", index=False)
#         return True
#     except sqlite3.Error:
#         return False

# # Generate SQL Query using GPT-4 
# def nl2sql_gpt4(nl_query, schema, column_name, table_name):
#     """Generates SQL query for semantic sorting using GPT-4."""
    
#     # Fetch unique column values
#     unique_values = get_unique_values(table_name, column_name)
#     if not unique_values:
#         return "No unique values found in the table."

#     # Construct the prompt
#     prompt = f"""Generate an SQL query that sorts the dataset **intelligently** based on the unique values present in the table.
    
#     ### **Sorting Logic**:
#     - Use these unique values: {', '.join(map(str, unique_values))}
#     - Infer sorting order based on meaning (e.g., job levels, degrees, countries).
#     - If order is unclear, use alphabetical sorting.

#     Sort the values based on their semantic meaning for the column. Try to avoid alphabetical sorting and use context and semantic relationships. Try to give an accurate SQL query with no errors and such.

#     **Schema**:
#     {schema}

#     **User Query**:
#     {nl_query}

#     **Output SQL Query (inside triple backticks like ```sql```)**:
#     Also, output the logic or explanation about the sorting order like why did you chose this sorting order (output it inside backticks and then explanation eg ```explanation [EXPLANATION TEXT]```)
#     """

#     response = openai.ChatCompletion.create(
#         model="gpt-4",
#         messages=[{"role": "user", "content": prompt}]
#     )

#     return response['choices'][0]['message']['content']

#     # return sql query and explanation from this func too -> implement

# def nl2sql_t5_semantic(nl_query, schema, column_name, table_name, unique_values):
#     """
#     Generates an SQL query for semantic sorting using a pretrained T5 model.

#     Args:
#     - nl_query (str): Natural language query from the user.
#     - schema (str): The SQL schema of the table.
#     - column_name (str): The column to be sorted.
#     - table_name (str): The table name.
#     - unique_values (list): Unique values from the column (to infer sorting logic).

#     Returns:
#     - (str, str): SQL query and explanation of sorting logic.
#     """

#     if not unique_values:
#         return None, "No unique values found in the table."

#     # Constructing a semantic sorting prompt
#     prompt = f"""Translate the following user request into an SQL query while ensuring **semantic sorting**:

#     ### **User Query:**
#     {nl_query}

#     ### **Table Information:**
#     - **Table Name:** {table_name}
#     - **Column to Sort:** {column_name}
#     - **Schema:** {schema}

#     ### **Sorting Logic:**
#     - **Unique Values in `{column_name}`:** {', '.join(map(str, unique_values))}
#     - **Sort based on real-world meaning**, not just alphabetical order.
#     - If values represent **job levels, academic degrees, age groups, or rankings**, order them **logically**.
#     - If values are **genres, categories, or qualitative terms**, order them from most imaginative to most realistic, or based on common human perception.
#     - If there's **no clear hierarchy**, use alphabetical sorting as a last resort.

#     ### **Output Format**:
#     - Return only the SQL query inside triple backticks (```sql```)
#     - Also, return a brief explanation of the sorting order inside triple backticks with `explanation` (```explanation```).

#     **Output Example:**
#     ```sql
#     SELECT * FROM {table_name} ORDER BY CASE {column_name} 
#         WHEN 'Senior' THEN 1 
#         WHEN 'Mid-Level' THEN 2 
#         WHEN 'Junior' THEN 3 
#         ELSE 4 END;
#     ```
#     ```explanation
#     The sorting prioritizes senior positions first, followed by mid-level, and junior positions last.
#     ```
#     """

#     # Tokenize input for the model
#     input_ids = tokenizer(prompt, return_tensors="pt").input_ids

#     # Generate response
#     output_ids = model.generate(input_ids, max_length=300)
#     response_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)

#     sql_query = extract_sql_query(response_text)
#     explanation = extract_explanation(response_text)

#     return sql_query, explanation


# # Extract SQL Query and Explanation from GPT Response

# def extract_sql_query(response_text):
#     match = re.search(r"```sql\s*\n(.*?)\n```", response_text, re.DOTALL)
#     if not match:
#         match = re.search(r"```\s*\n(.*?)\n```", response_text, re.DOTALL)
    
#     return match.group(1).strip() if match else None

# def extract_explanation(response_text):
#     match = re.search(r"```explanation\s*(.*?)```", response_text, re.DOTALL)
#     if not match:
#         match = re.search(r"```\s*(.*?)```", response_text, re.DOTALL)  # Generic fallback
    
#     return match.group(1).strip() if match else None

# def delete_table(table_name):
#     """Deletes the selected table from the database."""
#     try:
#         cursor = conn.cursor()
#         cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
#         conn.commit()
#         st.success(f"✅ Table `{table_name}` deleted successfully.")
#         st.cache_data.clear()  # Refresh table list in sidebar
#     except Exception as e:
#         st.error(f"❌ Error deleting table: {e}")


# # Streamlit UI
# st.title("NL2SQL Semantic Sorting")

# # Sidebar
# st.sidebar.header("📂 Database Management")
# mode = st.sidebar.radio("Choose Mode:", ["Query Existing Table", "Upload New Table"])

# tables = get_table_names()


# if mode == "Upload New Table":
#     st.header("📤 Upload Your Dataset")
#     uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

#     if uploaded_file:
#         df = pd.read_csv(uploaded_file)
#         st.write("### Preview of Uploaded Data:")
#         st.dataframe(df.head(), width=1000)

#         table_name = st.text_input("Enter table name for storing in the database:")

#         if table_name:
#             # Check if table exists
#             if table_name in get_table_names():
#                 st.warning(f"⚠️ Table `{table_name}` already exists! Choose another name.")
#             else:
#                 if create_table_if_not_exists(table_name, df):
#                     st.success(f"✅ Table `{table_name}` successfully created and data stored.")
#                     st.cache_data.clear()
#                     tables = get_table_names()
#                 # else:
#                 #     st.error("Failed to create table. Please try again.")

# elif mode == "Query Existing Table":
#     st.sidebar.header("📋 Available Tables")
#     tables = get_table_names()

#     for table in tables:
#         col1, col2 = st.sidebar.columns([3, 1])  # Sidebar layout
#         col1.write(f"📄 {table}")  # Show table name
#         if col2.button("❌", key=f"delete_{table}"):  # delete button for each table
#             delete_table(table)
#             # st.experimental_rerun()

#     selected_table = st.sidebar.selectbox("Choose a table", tables, index=0 if tables else None, key=1)

#     if selected_table:
#         df = pd.read_sql(f"SELECT * FROM {selected_table} LIMIT 100;", conn)
        
#         st.subheader(f"Preview of `{selected_table}` Table")
#         st.dataframe(df, width=1000)

#         # User Input for Sorting Query
#         st.header("Semantic Sorting")
#         nl_query = st.text_input("Enter your natural language sorting query:")

#         if nl_query:
#             column_name = st.selectbox("Select column to sort on:", df.columns, key=2)

#             if column_name:
#                 # Generating SQL
#                 schema = f"CREATE TABLE {selected_table} ({', '.join(df.columns)});"
#                 sql_query = nl2sql_gpt4(nl_query, schema, column_name, selected_table)
#                 extracted_sql = extract_sql_query(sql_query)
#                 # extracted_sql = None
#                 # unique_values = get_unique_values(selected_table, column_name)  # Fetch unique column values
        
#                 # sql_query, explanation = nl2sql_t5_semantic(nl_query, schema, column_name, selected_table, unique_values)
#                 # print(sql_query, explanation)

#                 if extracted_sql:
#                     st.subheader("📝 Generated SQL Query")
#                     st.code(extracted_sql, language="sql")
#                     explanation = extract_explanation(sql_query)

#                     # Execute SQL & Show Sorted table
#                     try:
#                         sorted_df = pd.read_sql(extracted_sql, conn)
#                         st.subheader("Sorted Table")
#                         st.dataframe(sorted_df, width=1000)
#                         st.write("### Sorting Explanation:")
#                         st.write(explanation)
#                     except Exception as e:
#                         st.error(f"⚠️ SQL Execution Error: {e}")
#                 else:
#                     st.error("🚨 No valid SQL query found in GPT's response.")


# '''
# This is the second version, where we store the sorting orders of a particular column with their explanation and tags in the database.
# We also store embedding of the explanation in the database.

# When a user inputs a sorting query, we take the embedding of this query and find the best explanation embedding from the stored orderings 
# (using cosine similarity) and then generate a SQL query using that sorting order to sort the query.
# '''

import streamlit as st
import sqlite3
import pandas as pd
import openai
import json
import re
import numpy as np
from numpy.linalg import norm

openai.api_key = st.secrets["OPENAI_API_KEY"]

DB_PATH = "database.db"

@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

conn = get_connection()

# @st.cache_data
def get_table_names():
    query = "SELECT name FROM sqlite_master WHERE type='table';"
    return pd.read_sql(query, conn)["name"].tolist()

# Helper: Generate an embedding for a given text 
def get_embedding(text):
    response = openai.Embedding.create(input=text, model="text-embedding-ada-002")
    return response["data"][0]["embedding"]

# Generate Semantic Sorting Orders from OpenAI 
def generate_semantic_sort_orders(values, column_name):
    """
    Uses API to generate multiple semantic sorting orders for a given column.
    """
    
    prompt = f"""
    You are an expert in data semantics and contextual ranking. Your task is to analyze the values {values} 
    for the column '{column_name}' and determine the best possible sorting orders based on their **semantic meaning**. 
    **Avoid alphabetical sorting unless explicitly relevant.**
    
    **Instructions:**
    1. Provide **at least 5 different sorting orders** based on different meaningful criteria.
    2. Each sorting order should be **explained in detail** (why this order makes sense).
    3. **Ensure maximum relevance** to how the values are used in real-world scenarios.
    4. **Use newline separation** (add 2 new lines after every sorting order).

    **Output Format Example:**
    ```
    Sorting Order Name: Importance Ranking
    Sorted Values: [Most Important, Moderately Important, Least Important]
    Explanation: Items are ranked based on their significance in professional settings.

    Sorting Order Name: Usage Frequency
    Sorted Values: [Most Used, Occasionally Used, Rarely Used]
    Explanation: Values are sorted based on how often they are referenced.

    Sorting Order Name: Numerical Priority
    Sorted Values: [Highest, Medium, Lowest]
    Explanation: Ranking is based on numerical significance, e.g., scores, ratings.
    ```
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]


# def generate_sorting_orders_with_tags(values, column_name):
#     """
#     Uses OpenAI API to generate multiple semantic sorting orders for a given column along with grouping tags.
#     """
    
#     prompt = f"""
#     You are an expert in data classification and ranking. Your task is to:
#     1. Analyze the values {values} for the column '{column_name}' and generate **at least 5 semantic sorting orders**.
#     2. Each sorting order must have a **clear explanation** of why it is meaningful.
#     3. **Additionally, assign a generic tag** (e.g., "size", "economic", "chronological", "importance") to categorize the sorting orders.
#     4. **Ensure sorting orders with similar logic have the same tag.** Do not create different tags for similar sorting orders.
#     5. **Use newline separation** (add 2 new lines after every sorting order).
    

#     **Output Format Example:**
#     ```
#     Sorting Order Name: GDP Ranking
#     Sorted Values: ['USA', 'Germany', 'UK', 'Canada']
#     Explanation: The values are sorted based on the Gross Domestic Product (GDP) of each country.
#     Tag: economy

#     Sorting Order Name: Population Size
#     Sorted Values: ['USA', 'Germany', 'UK', 'Canada']
#     Explanation: This order is based on the population size.
#     Tag: size

#     Sorting Order Name: Geographic Size
#     Sorted Values: ['Canada', 'USA', 'Germany', 'UK']
#     Explanation: Countries are sorted by land area.
#     Tag: size
#     ```
#     """

#     response = openai.ChatCompletion.create(
#         model = "gpt-4",
#         messages = [{"role": "user", "content": prompt}]
#     )

#     return response["choices"][0]["message"]["content"]



def generate_sorting_orders_with_tags(values, column_name):
    """
    Uses OpenAI API to generate multiple semantic sorting orders for a given column along with grouping tags.
    Also, fetches real-world criteria values if relevant.
    """

    prompt = f"""
    You are an expert in data classification and ranking. Your task is to:
    1. Analyze the values {values} for the column '{column_name}' and generate **at least 5 semantic sorting orders** Remember the sorting orders should only contain the values provided, no extra values eg if there are 5 values, then the sorting orders can only contain 5 values.
    2. Each sorting order must have a **clear explanation** of why it is meaningful.
    3. **Additionally, assign a generic tag** (e.g., "size", "economic", "chronological", "importance") to categorize the sorting orders.
    4. **If a sorting order is based on real-world measurable data (e.g., GDP, land size, population, or anything like that), specify the criteria needed.**
    5. **Ensure sorting orders with similar logic have the same tag.** Do not create different tags for similar sorting orders.
    6. **Use newline separation** (add 2 new lines after every sorting order).
    
    **Output Format Example:**
    ```
    Sorting Order Name: GDP Ranking
    Sorted Values: ['USA', 'Germany', 'UK', 'Canada']
    Explanation: The values are sorted based on the Gross Domestic Product (GDP) of each country.
    Tag: economy
    Criteria Needed: GDP (Trillion USD)

    Sorting Order Name: Population Size
    Sorted Values: ['USA', 'Germany', 'UK', 'Canada']
    Explanation: This order is based on the population size.
    Tag: size
    Criteria Needed: Population

    Sorting Order Name: Geographic Size
    Sorted Values: ['Canada', 'USA', 'Germany', 'UK']
    Explanation: Countries are sorted by land area.
    Tag: size
    Criteria Needed: Land Area

    ```
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]

def parse_and_store_sort_orders(table_name, column_name, response_text, is_tag):
    """
    Parses the OpenAI response and stores sorting orders, explanations, and tags (if applicable) in the database.
    """
    sort_orders = []

    # regex for handling optional newlines and spacing issues
    if is_tag:
        # pattern = r"Sorting Order Name:\s*(.*?)\s*\n\s*Sorted Values:\s*\[(.*?)\]\s*\n\s*Explanation:\s*(.*?)\s*\n\s*Tag:\s*(.*?)\s*(?:\n|$)"
        pattern = r"Sorting Order Name:\s*(.*?)\s*\n\s*Sorted Values:\s*\[(.*?)\]\s*\n\s*Explanation:\s*(.*?)\s*\n\s*Tag:\s*(.*?)\s*\n\s*Criteria Needed:\s*(.*?)\s*(?:\n|$)"
    else:
        pattern = r"Sorting Order Name:\s*(.*?)\s*\n\s*Sorted Values:\s*\[(.*?)\]\s*\n\s*Explanation:\s*(.*?)\s*(?:\n|$)"

    matches = re.findall(pattern, response_text, re.DOTALL)

    print(f"🔍 Extracted {len(matches)} sorting orders from response")  # Debugging

    for match in matches:
        order_name = match[0].strip()
        sorted_values = [x.strip().strip("'").strip('"') for x in match[1].split(",")]
        explanation = match[2].strip()

        tag = match[3].strip().lower() if is_tag and len(match) > 3 else "unknown"  # Default to "unknown" if missing
        criteria_needed = match[4].strip()

        sort_orders.append((order_name, sorted_values, explanation, tag, criteria_needed))

    cursor = conn.cursor()

    if is_tag:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sorting_metadata_tags_criteria (
                table_name TEXT,
                column_name TEXT,
                sorting_name TEXT,
                sorting_order TEXT,
                explanation TEXT,
                tag TEXT,
                criteria_name TEXT,
                embeddings TEXT
            )
        """)
        insert_query = "INSERT INTO sorting_metadata_tags_criteria (table_name, column_name, sorting_name, sorting_order, explanation, tag, criteria_name, embeddings) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sorting_metadata (
                table_name TEXT,
                column_name TEXT,
                sorting_name TEXT,
                sorting_order TEXT,
                explanation TEXT,
                embeddings TEXT
            )
        """)
        insert_query = "INSERT INTO sorting_metadata (table_name, column_name, sorting_name, sorting_order, explanation, embeddings) VALUES (?, ?, ?, ?, ?, ?)"

    # Insert data
    for order_name, sorted_values, explanation, tag, criteria_needed in sort_orders:
        embedding = get_embedding(order_name + " " + explanation)
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        if is_tag:

            if criteria_needed and criteria_needed not in existing_columns:
                # Fetch missing criteria values from GPT
                criteria_values = fetch_missing_criteria_values(sorted_values, column_name, criteria_needed)

               # Ensure table_name and criteria_needed are properly formatted (Avoid SQL Injection risk)
                table_name = table_name.strip().replace(";", "")  # Basic sanitization
                criteria_needed = criteria_needed.strip().replace(";", "")

                # Add new column to table
                cursor.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{criteria_needed}" TEXT')

                # Update table with new values
                for item, value in criteria_values.items():
                    cursor.execute(f'UPDATE "{table_name}" SET "{criteria_needed}" = ? WHERE "{column_name}" = ?', (value, item))
            print("inserting")
            cursor.execute(insert_query, (table_name, column_name, order_name, json.dumps(sorted_values), explanation, tag, criteria_needed, json.dumps(embedding)))
            print("inserted")
        else:
            # cursor.execute(insert_query, (table_name, column_name, order_name, json.dumps(sorted_values), explanation, json.dumps(embedding)))
            pass

        print(f"✅ Stored: {order_name} | {sorted_values} | {explanation} | {tag}")  # Debugging

    conn.commit()
    print(f"Successfully inserted {len(sort_orders)} sorting orders into {'sorting_metadata_tags' if is_tag else 'sorting_metadata'}")

def fetch_missing_criteria_values(values, column_name, criteria):
    """
    Queries GPT-4 to generate real-world values (e.g., GDP, land size) for given values.
    """
    prompt = f"""
    You are an expert in global data. Given the following {column_name}: {values}, 
    provide their {criteria}. Ensure that all values are realistic and up to date.
    If the values are numeric, just give numeric values or the numbers, don't give the unit or measurement.
    E.g., if it's 1 million, give only 1, if its 30 million, give 30, if its 238 sq.km give only 238, etc

    **Format:**
    ```
    {values[0]}: <value>
    {values[1]}: <value>
    ...
    ```
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response["choices"][0]["message"]["content"]
    extracted_values = {}
    for line in response_text.split("\n"):
        if ":" in line:
            key, val = line.split(":")
            extracted_values[key.strip()] = val.strip()

    return extracted_values  # Returns a dictionary {Country: GDP}

# Calculating similarity between two embeddings
def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (norm(vec1) * norm(vec2))

# WITH TAGS

def find_best_matching_tag(table_name, column_name, user_query):
    """
    Finds the best tag that matches the user's query.
    """

    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT tag FROM sorting_metadata_tags WHERE table_name=? AND column_name=?", (table_name, column_name))
    tags = [row[0] for row in cursor.fetchall()]

    if not tags:
        return None

    user_query_embedding = get_embedding(user_query)

    best_tag = None
    highest_similarity = -1

    for tag in tags:
        if "alphabetical" not in tag.lower():
            tag_embedding = get_embedding(tag)
            similarity = cosine_similarity(user_query_embedding, np.array(tag_embedding))

            # print(f"Similarity with tag {tag}: {similarity}")

            if similarity > highest_similarity:
                highest_similarity = similarity
                best_tag = tag
        
    return best_tag

def find_best_matching_sorting(table_name, column_name, user_query):
    """
    Finds the best sorting order using stored embeddings.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT sorting_name, sorting_order, explanation, embeddings FROM sorting_metadata WHERE table_name=? AND column_name=?", 
                   (table_name, column_name))
    sorting_options = cursor.fetchall()

    if not sorting_options:
        return None, None

    user_query_embedding = get_embedding(user_query)
    best_match = None
    best_sort_order = None
    highest_similarity = -1

    for name, order_json, explanation, embeddings_json in sorting_options:
        stored_embedding = json.loads(embeddings_json)
        similarity = cosine_similarity(user_query_embedding, np.array(stored_embedding))

        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = explanation
            best_sort_order = json.loads(order_json)

    print(highest_similarity, best_sort_order, best_match)
    return highest_similarity, best_sort_order, best_match

def find_best_matching_sorting_with_tag(table_name, column_name, user_query):
    """
    Finds the best sorting order by first identifying the relevant tag and then searching under that tag.
    """
    
    best_tag = find_best_matching_tag(table_name, column_name, user_query)
    if not best_tag:
        return None, None, None
    
    
    cursor = conn.cursor()
    cursor.execute("SELECT sorting_name, sorting_order, explanation, embeddings FROM sorting_metadata_tags WHERE table_name=? AND column_name=? AND tag=?",
                   (table_name, column_name, best_tag))
    
    sorting_options = cursor.fetchall()

    if not sorting_options:
        return None, None
    
    user_query_embedding = get_embedding(user_query)
    best_match = None
    best_sort_order = None
    highest_similarity = -1

    for name, order_json, explanation, embeddings_json in sorting_options:
        stored_embedding = json.loads(embeddings_json)
        similarity = cosine_similarity(user_query_embedding, np.array(stored_embedding))

        if similarity > highest_similarity:
            highest_similarity = similarity
            best_sort_order = json.loads(order_json)
            best_match = explanation

    return highest_similarity, best_sort_order, best_match


# Convert Sorting Order to SQL Query 
def generate_sql_query_for_sorting(table_name, column_name, sorting_order):
    """
    Generates an SQL query that orders the given column based on a precomputed sorting order.
    """
    case_parts = []
    
    for idx, val in enumerate(sorting_order):
        case_parts.append(f"WHEN '{val.replace('\'', '')}' THEN {idx}")  # Ensures correct single quotes

    case_statement = f"CASE {column_name} " + " ".join(case_parts) + f" ELSE {len(sorting_order)} END"
    query = f"SELECT * FROM {table_name} ORDER BY {case_statement};"
    
    return query


# Streamlit UI
st.title("Semantic NL2SQL Sorting System")

# Mode Selection
mode = st.sidebar.radio("Mode:", ["Upload New Table", "Query Existing Table", "Generate sorting orders for a column"])

# Upload New Table
if mode == "Upload New Table":
    st.header("Upload Your CSV")
    uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.write("Preview:", df.head())

        table_name = st.text_input("Enter table name:")

        if table_name:
            # Checking if table exists
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            table_exists = cursor.fetchone()

            if table_exists:
                st.warning(f"Table '{table_name}' already exists! Choose another name or overwrite it.")

                overwrite = st.checkbox(f"Overwrite existing '{table_name}' table?")
                if overwrite:
                    cursor.execute(f"DROP TABLE {table_name}")  # Delete existing table
                    conn.commit()
                    st.info(f"Table '{table_name}' deleted. You can now upload a new version.")

            if not table_exists or overwrite:
                try:
                    df.to_sql(table_name, conn, if_exists="replace", index=False)  # Replace existing table
                    st.success(f"Table '{table_name}' successfully created.")

                    # --- Column selection (Fix) ---
                    # column_name = st.selectbox("Select a column to generate sorting orders:", df.columns, key="column_selection")

                    # if column_name:  # Wait until the user selects a column
                    #     unique_vals = pd.read_sql(f"SELECT DISTINCT {column_name} FROM {table_name}", conn)[column_name].dropna().tolist()

                    #     if unique_vals:
                    #         response_text = generate_semantic_sort_orders(unique_vals, column_name)
                    #         parse_and_store_sort_orders(table_name, column_name, response_text)
                    #         st.success(f"Semantic sorting orders stored for '{column_name}'.")

                except Exception as e:
                    st.error(f"❌ Error: {e}")

# Query Existing Table
elif mode == "Query Existing Table":
    st.sidebar.header("Available Tables")
    tables = get_table_names()
    selected_table = st.sidebar.selectbox("Select a table", tables)
    
    if selected_table:
        df = pd.read_sql(f"SELECT * FROM {selected_table} LIMIT 100;", conn)
        st.write("Table Preview:", df)

        column_name = st.selectbox("Select column to sort on:", [None] + list(df.columns))
        nl_query = st.text_input("Enter your sorting query (in natural language):")

        if nl_query and column_name:

            # WITH TAGS
            highest_similarity, best_sorting_order, matched_explanation = find_best_matching_sorting_with_tag(selected_table, column_name, nl_query)
            if best_sorting_order:
                st.write(f"Matched Explanation: \"{matched_explanation}\"")
                st.write(f"Sorting Order: {', '.join(best_sorting_order)}")

                sql_query = generate_sql_query_for_sorting(selected_table, column_name, best_sorting_order)
                st.code(sql_query, language="sql")

                sorted_df = pd.read_sql(sql_query, conn)
                st.write("Sorted Table:")
                st.dataframe(sorted_df)

            else:
                st.error("No matching sorting order found.")

elif mode == "Generate sorting orders for a column":
    st.sidebar.header("Available Tables")
    tables = get_table_names()
    selected_table = st.sidebar.selectbox("Select a table", tables)

    if selected_table:
        df = pd.read_sql(f"SELECT * FROM {selected_table} LIMIT 100;", conn)
        st.write("Table Preview:", df)

        columns = df.columns
        column_name = st.selectbox("Select a column: ", [None] + list(columns))


        if column_name:
            try:
                unique_vals = pd.read_sql(f"SELECT DISTINCT {column_name} FROM {selected_table}", conn)[column_name].dropna().tolist()

                if unique_vals:
                    print(unique_vals)

                    # WITHOUT TAGS
                    # response_text = generate_semantic_sort_orders(unique_vals, column_name)

                    # WITH TAGS
                    response_text = generate_sorting_orders_with_tags(unique_vals, column_name)
                    # WITHOUT TAGS and WITH TAGS
                    is_tag = True
                    print("RESPONSE TEXT:", response_text)
                    parse_and_store_sort_orders(selected_table, column_name, response_text, is_tag)

                    st.success(f"✅ Semantic sorting orders stored for '{column_name}'.")
            
            except Exception as e:
                st.error(f"❌ Error: {e}")
        


