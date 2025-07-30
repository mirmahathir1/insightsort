import os
import shutil
from pathlib import Path
import base64
import traceback
import streamlit as st
import pandas as pd
import duckdb

from prompts import build_suggestion_prompt, generate_augmented_sql_prompt
from llm_utils import call_gpt, parse_suggestion
from index_builder import build_indexes_from_datalake
from join_discovery import load_indexes, discover_augmentable_column
from semantic_score import (
    compute_semantic_interestingness,
    update_suggestions_with_semantic_scores,
)

# ───────────────────── Connections / Globals ─────────────────────────────────
if "con" not in st.session_state:                # ① create once
    st.session_state.con = duckdb.connect()
con = st.session_state.con                       # reuse thereafter

# logo of InsightSort
with open("insightsort_logo.png", "rb") as image_file:
    encoded_image = base64.b64encode(image_file.read()).decode()

# global state helpers
global_col = ""
global_source = ""

# ───────────────────── Session‑state defaults ────────────────────────────────
if "data_lake" not in st.session_state:
    st.session_state.data_lake = {}

if "sorting_suggestions" not in st.session_state:
    st.session_state.sorting_suggestions = {}

if "uploaded_table" not in st.session_state:
    st.session_state.uploaded_table = None

if "suggestions_df" not in st.session_state:
    st.session_state.suggestions_df = None

if "confirmed_sort_option" not in st.session_state:
    st.session_state.confirmed_sort_option = None

if "show_sql_result" not in st.session_state:
    st.session_state.show_sql_result = False

if "apply_sort_clicked" not in st.session_state:
    st.session_state.apply_sort_clicked = False

if "augment_data_clicked" not in st.session_state:
    st.session_state.augment_data_clicked = False

if "apply_augmentation_clicked" not in st.session_state:
    st.session_state.apply_augmentation_clicked = False

if "input_table_files" not in st.session_state:
    st.session_state.input_table_files = []

# ───────────────────── Page config & theme tweaks ────────────────────────────
st.set_page_config(page_title="InsightSort", layout="wide")

st.markdown(
    """
<style>
div.stButton > button[kind="primary"] {
    background-color: #e3f2fd;
    color: #0d47a1;
    border: 1px solid #90caf9;
    font-weight: 600;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #bbdefb;
}
</style>
""",
    unsafe_allow_html=True,
)

# ───────────────────── Top banner ────────────────────────────────────────────
st.markdown(
    f"""
<div style="display: inline-flex; align-items: center; justify-content: flex-start; margin-bottom: 15px; margin-top: -12px;">
    <span style="font-size: 42px; font-weight: bold;">InsightSort</span>
    <img src="data:image/png;base64,{encoded_image}" width="50" style="margin-left: 15px;" />
</div>
""",
    unsafe_allow_html=True,
)
st.markdown(
    """
<p style="font-weight: 600; font-size: 1.1rem;">
    Discover meaningful ways to sort your tables!
</p>
<p style="font-size: 1rem; margin-top: -10px;">
    InsightSort helps you explore your data by recommending smart, semantically
    interesting attributes to sort by — even if those attributes aren’t in your
    original table.
</p>
""",
    unsafe_allow_html=True,
)

# ───────────────────── Sidebar header ────────────────────────────────────────
st.sidebar.markdown(
    f"""
<div style="display: inline-flex; align-items: center; justify-content: flex-start; margin-top: 20px">
    <span style="font-size: 24px; font-weight: bold;">InsightSort</span>
    <img src="data:image/png;base64,{encoded_image}" width="30" style="margin-left: 10px;" />
</div>
""",
    unsafe_allow_html=True,
)

# ───────────────────── Data‑lake picker ───────────────────────────────────────
DATALAKES_ROOT = "datalakes"  # ./datalakes/datalake1/, datalake2/, …

st.sidebar.header("🏞️  Data‑lake")

datalake_opts = [
    d
    for d in os.listdir(DATALAKES_ROOT)
    if (Path(DATALAKES_ROOT) / d).is_dir()
]
if not datalake_opts:
    datalake_opts = ["<no datalakes found>"]

# No data‑lake is pre‑selected (index=None) so the user must choose one
chosen_lake = st.sidebar.selectbox(
    "Select a data lake",
    options=datalake_opts,
    index=None,
    placeholder="Choose a data lake…",
)

# Load / switch data‑lake
if chosen_lake:  # only proceed if the user actually picked one
    if (
        "chosen_lake" not in st.session_state
        or st.session_state.chosen_lake != chosen_lake
    ):
        # ─── Fresh lake selected — reset relevant state ───────────────────────
        st.session_state.chosen_lake = chosen_lake
        st.session_state.data_lake.clear()
        st.session_state.uploaded_table = None
        st.session_state.input_table_files = []

        if chosen_lake != "<no datalakes found>":
            lake_dir   = Path(DATALAKES_ROOT) / chosen_lake
            tables_dir = lake_dir / "all_tables"
            index_dir  = lake_dir / "index_files"
            input_dir  = lake_dir / "input_tables"

            # 1️⃣ Read every CSV in all_tables/*
            for csv_path in tables_dir.glob("*.csv"):
                try:
                    st.session_state.data_lake[csv_path.stem] = pd.read_csv(csv_path)
                except Exception as e:
                    st.warning(f"⚠️  Failed to read {csv_path.name}: {e}")

            # 2️⃣ Ensure indexes exist (build if missing/empty)
            if not index_dir.exists() or not any(index_dir.iterdir()):
                with st.spinner(f"Building indexes for '{chosen_lake}' …"):
                    build_indexes_from_datalake(
                        st.session_state.data_lake, save_dir=index_dir
                    )
                st.success("✅ Indexes built and stored in the data‑lake.")

            # 3️⃣ Copy/refresh indexes into project‑root ./index_files
            dest = Path("index_files")
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(index_dir, dest)

            # 4️⃣ Collect available input tables (but don’t load yet)
            if input_dir.exists():
                st.session_state.input_table_files = list(input_dir.glob("*.csv"))
            else:
                st.session_state.input_table_files = []

            st.success(
                f"✅ Loaded data lake “{chosen_lake}” "
                f"({len(st.session_state.data_lake)} tables)."
            )
        else:
            st.warning("No data‑lake directories found under ./datalakes/.")

# ───────────────────── Sidebar: Input‑table picker ───────────────────────────
selected_input_name = None          # define once, keep in scope

if st.session_state.get("chosen_lake") \
   and st.session_state.chosen_lake != "<no datalakes found>":

    st.sidebar.header("📂 Input Table")

    input_table_names = [
        p.stem for p in st.session_state.get("input_table_files", [])
    ]

    if input_table_names:
        selected_input_name = st.sidebar.selectbox(
            "Select an input table",
            options=input_table_names,
            index=None,
            placeholder="Choose an input table…",
        )
    else:
        st.sidebar.write(
            "*No input tables found in this data‑lake’s `input_tables/` folder.*"
        )
# else: no data‑lake selected → don’t show the picker


# Load input table when selected
if selected_input_name:
    # If the selected table changed, or none was loaded yet → load it
    if (
        st.session_state.uploaded_table is None
        or st.session_state.uploaded_table.attrs.get("name") != selected_input_name
    ):
        # Find the corresponding file path
        for p in st.session_state.input_table_files:
            if p.stem == selected_input_name:
                try:
                    st.session_state.uploaded_table = pd.read_csv(p)
                    # Tag the DataFrame so we can detect changes later
                    st.session_state.uploaded_table.attrs["name"] = selected_input_name
                    con.register("input_table", st.session_state.uploaded_table)
                    st.success(f"✅ Loaded input table “{selected_input_name}”.")
                except Exception as e:
                    st.error(f"Failed to read {p.name}: {e}")
                break

# ───────────────────── Main‑page: Show data‑lake tables ──────────────────────
if st.session_state.data_lake:
    st.subheader("Data Lake Tables 📚")
    datalake_table_names = list(st.session_state.data_lake.keys())
    selected_datalake_table = st.selectbox(
        "Select a table to view it here:", datalake_table_names
    )

    if selected_datalake_table:
        st.write(f"**{selected_datalake_table}**")
        st.dataframe(st.session_state.data_lake[selected_datalake_table])

# ───────────────────── Main‑page: Show input table ───────────────────────────
if st.session_state.uploaded_table is not None:
    st.subheader("Input Table:")
    st.dataframe(st.session_state.uploaded_table)
    # drop any existing view/table with that name
    con.execute("DROP VIEW IF EXISTS input_table")
    con.execute("DROP TABLE IF EXISTS input_table")
    # register the current DataFrame
    con.register("input_table", st.session_state.uploaded_table)


# Only generate suggestions if an input table is loaded AND suggestions haven't been generated yet
if st.session_state.uploaded_table is not None and not st.session_state.sorting_suggestions:
    df = st.session_state.uploaded_table

    if st.button("Get Suggestions 💡"):
        try:
            sample_rows = df.head(5).to_dict(orient="records")
            column_names = list(df.columns)

            with st.spinner("Thinking of smart ways to sort your table..."):
                prompt = build_suggestion_prompt(sample_rows, column_names)
                gpt_response = call_gpt(prompt)
                # print("gpt response: ", gpt_response)
                suggestions = parse_suggestion(gpt_response)
                st.session_state.sorting_suggestions = suggestions

                if st.session_state.sorting_suggestions:
                    table_rows = []
                    for base_col, sort_list in suggestions.items():
                        for suggestion in sort_list:
                            table_rows.append({
                                "Base Column": base_col,
                                "Sort Attribute": suggestion.get("column"),
                                "Description": suggestion.get("description"),
                                "Interestingness": suggestion.get("interestingness", ""),
                                "Required Column": suggestion.get("required_column"),
                                "Column present": suggestion.get("column present in the table"),
                            })

                    st.session_state.suggestions_df = pd.DataFrame(table_rows)

                    input_columns = list(st.session_state.suggestions_df.columns)
                    # print(st.session_state.suggestions_df)
                    st.session_state.suggestions_df = update_suggestions_with_semantic_scores(
                        st.session_state.suggestions_df,
                        input_columns
                    )
                    # print(st.session_state.suggestions_df)
                    st.session_state.suggestions_df.index = st.session_state.suggestions_df.index + 1

                else:
                    st.warning("Could not generate sorting suggestions.")
                    st.session_state.suggestions_df = None # Ensure it's None if no suggestions
        except Exception as e:
            st.error(f"Error generating suggestions: {e}")
            st.session_state.sorting_suggestions = {}
            st.session_state.suggestions_df = None

# --- Display Suggestions and Selection Form ---
if st.session_state.suggestions_df is not None and not st.session_state.suggestions_df.empty:
        st.subheader("🔍 Sorting Suggestions")
        sorted_suggestions_df = st.session_state.suggestions_df.groupby("Base Column", group_keys=False).apply(lambda x: x.sort_values("Interestingness", ascending=False))
        st.table(sorted_suggestions_df)

        input_columns = list(st.session_state.uploaded_table.columns)
        candidate_columns = list(st.session_state.suggestions_df["Sort Attribute"])

        semantic_interestingness = compute_semantic_interestingness(input_columns, candidate_columns)

        st.write(f"Semantic Utility score: {semantic_interestingness}")

        df_suggestions = st.session_state.suggestions_df

        # Generate unique readable options for user selection
        select_options = [
            f"{row['Base Column']} ➝ {row['Sort Attribute']}"
            for _, row in sorted_suggestions_df.iterrows()
        ]

        select_options_with_prompt = ["-- Select --"] + select_options


        with st.form(key="sort_selection_form"):

            selected_option_in_form = st.selectbox(
                "Choose a suggestion:",
                select_options_with_prompt,
                index=0, # Default to "-- Select --"
                key="suggestion_selectbox" # Assign a key for stability within the form
            )

            submited = st.form_submit_button("⚙️ Generate SQL Query for this Sort")

            if submited:

                # reset the booleans corresponding to the button clicks
                st.session_state.apply_sort_clicked = False
                st.session_state.augment_data_clicked = False
                st.session_state.apply_augmentation_clicked = False


                if selected_option_in_form != "-- Select --":
                    # store the confirmed selection in session state
                    st.session_state.confirmed_sort_option = selected_option_in_form
                    st.session_state.show_sql_result = True
                else:
                    st.warning("Please select a sorting suggestion first.")
                    # Reset if user clicks button without selection
                    st.session_state.confirmed_sort_option = None
                    st.session_state.show_sql_result = False

if st.session_state.show_sql_result and st.session_state.confirmed_sort_option and st.session_state.suggestions_df is not None:


    # Find the selected row based on the confirmed option stored in session state
    # Regeberate options to find index reliably (needed because index might change)
    df_suggestions = st.session_state.suggestions_df
    current_select_options = [
        f"{row['Base Column']} ➝ {row['Sort Attribute']}"
        for _, row in df_suggestions.iterrows()
    ]

    # Find the index based on the confirmed option string
    selected_idx = current_select_options.index(st.session_state.confirmed_sort_option)
    selected_row = df_suggestions.iloc[selected_idx]
    sort_info = selected_row.to_dict()

    base_col = selected_row["Base Column"]
    sort_attr = selected_row["Sort Attribute"]
    description = selected_row["Description"]
    required_col = selected_row["Required Column"]
    input_cols = list(st.session_state.uploaded_table.columns)

    col_exp1, col_exp2 = st.columns([1, 1])

    with col_exp1:
        with st.expander("📊 Selected Sort Option", expanded=True):
            st.markdown(
                f"""
                <div style='
                    background-color: #fffde7;
                    padding: 12px 16px;
                    border-radius: 8px;
                    border-left: 4px solid #90caf9;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                '>
                    <p style='
                        margin: 0;
                        font-size: 17px;
                        font-weight: 600;
                        color: #333;
                    '>
                        Sort Attribute:
                        <span style='
                            color: #1565c0;
                            font-weight: 600;
                            padding-left: 4px;
                        '>{sort_info['Sort Attribute']}</span>
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("<br>", unsafe_allow_html=True)

            interestingness = float(sort_info['Interestingness'])
            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("<div style='background-color:#f9f9f9; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                st.markdown("#### Column Information")
                st.markdown(f"**Base Column:** `{sort_info['Base Column']}`")
                st.markdown(f"**Required Column:** `{sort_info['Required Column']}`")
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                is_present = sort_info.get('Column present', 'No') == 'Yes'
                status_bg = "#E8F5E9" if is_present else "#FFF8E1"
                status_color = "#2E7D32" if is_present else "#FF8F00"
                status_icon = "✅" if is_present else "ℹ️"
                status_text = "Required column is available in the input table" if is_present else "Required column(s) needs to be joined from the data lake"

                st.markdown(
                    f"""
                    <div style='background-color:{status_bg}; padding:10px; border-radius:6px;'>
                        <p style='margin:0; font-size:16px; color:{status_color}; font-weight:600;'>{status_icon} {status_text}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with col2:
                st.markdown("<div style='background-color:#f3e5f5; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                st.markdown("#### 💡 Insight Value")
                st.progress(interestingness)
                st.markdown(f"**Interestingness Score:** `{interestingness:.2f}`")
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                st.markdown("<div style='background-color:#e8eaf6; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                st.markdown("#### 📜 Description")
                st.markdown(f"*{sort_info['Description']}*")
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if not is_present:
                    if st.button("🔍 Augment Missing Data", type="primary", key="augment_data"):
                        st.session_state.augment_data_clicked = True
                else:
                    if st.button("✅ Apply Sort", type="primary", key="apply_sort"):
                        st.session_state.apply_sort_clicked = True

    with col_exp2:
        if st.session_state.augment_data_clicked:
            join_index, semantic_index = load_indexes("index_files")
            augment_data = discover_augmentable_column(sort_attr, st.session_state.uploaded_table, st.session_state.data_lake, semantic_index, join_index, 5)

            with st.expander("✨ Suggested Semantic Augmentation", expanded=True):
                st.markdown(
                    f"""
                    <div style='
                        background-color: #f1f8e9;
                        padding: 12px 16px;
                        border-radius: 8px;
                        border-left: 4px solid #4CAF50;
                        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
                    '>
                        <p style='
                            margin: 0;
                            font-size: 17px;
                            font-weight: 600;
                            color: #2e7d32;
                        '>
                            Suggested Attribute:
                            <span style='
                                color: #1b5e20;
                                font-weight: 600;
                                padding-left: 4px;
                            '>{augment_data['suggested_attribute']}</span>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                st.markdown("<br>", unsafe_allow_html=True)

                # Convert numpy values to Python float if needed
                sem_dist = float(augment_data['semantic_distance'])
                join_dist = float(augment_data['join_distance'])
                
                # Create two columns for the data
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("<div style='background-color:#f9f9f9; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                    st.markdown("#### 📂 Source Information")
                    st.markdown(f"**Table:** `{augment_data['matched_table']}`")
                    st.markdown(f"**Column:** `{augment_data['matched_column']}`")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Display join quality with visual indicator
                    st.markdown("<div style='background-color:#fff3e0; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                    st.markdown("#### 🔗 Join Quality")
                    # Create a progress bar for join distance (inverted since lower is better)
                    join_quality = max(0, min(1.0, 1.0 - join_dist)) if join_dist <= 1.0 else 0
                    st.progress(join_quality)
                    st.markdown(f"**Join Distance:** `{join_dist:.4f}`")
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with col2:
                    st.markdown("<div style='background-color:#f9f9f9; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                    st.markdown("#### Join Configuration")
                    st.markdown(f"**Input Table Key:** `{augment_data['join_key_input']}`")
                    st.markdown(f"**Data Lake Table Key:** `{augment_data['join_key_datalake']}`")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Display semantic quality with visual indicator
                    st.markdown("<div style='background-color:#e3f2fd; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                    st.markdown("#### Semantic Match")
                    # Create a progress bar for semantic distance (inverted since lower is better)
                    semantic_quality = max(0, min(1.0, 1.0 - sem_dist)) if sem_dist <= 1.0 else 0
                    st.progress(semantic_quality)
                    st.markdown(f"**Semantic Distance:** `{sem_dist:.4f}`")
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # Add action buttons at the bottom
                st.markdown("<br>", unsafe_allow_html=True)
                col_btn1, col_btn2 = st.columns([1, 1])
                
                with col_btn1:
                    if st.button("✅ Apply Augmentation", type="primary", key="apply_aug"):
                            st.session_state.apply_augmentation_clicked = True
                with col_btn2:
                    st.button("🔎 Preview Data", key="preview_aug")


        
        # proceeding with sql generation

    if selected_row["Column present"] == "Yes":

        if st.session_state.apply_sort_clicked:

            with st.spinner("Generating SQL query to sort your table..."):    
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

        Return only the SQL query — no explanations or markdown formatting. Also don't include it in backticks 
        OUTPUT
        like this. Just give a normal string output.
        """

                try:
                    sql_response = call_gpt(sql_prompt).strip()

                    if sql_response:
                        st.markdown("### 🧾 SQL Query to Sort Your Table")
                        st.code(sql_response, language="sql")

                        result_df = con.execute(sql_response).df()
                        st.dataframe(result_df)
                    else:
                        st.error("⚠️ Could not generate SQL query. Please try again.")
                except Exception as e:
                        st.error(f"⚠️ Error calling LLM for SQL generation: {e}")
                        print(traceback.format_exc())  # or st.text()
        
    if st.session_state.augment_data_clicked:
        join_index, semantic_index = load_indexes("index_files")

        augment_data = discover_augmentable_column(sort_attr, st.session_state.uploaded_table, st.session_state.data_lake, semantic_index, join_index, 5)
        
        if st.session_state.apply_augmentation_clicked:
            if augment_data is not None:
                input_table = st.session_state.uploaded_table
                datalake_table_name = augment_data["matched_table"]
                datalake_table = st.session_state.data_lake[datalake_table_name]
                input_table_key = augment_data["join_key_input"]
                datalake_table_key = augment_data["join_key_datalake"]
                sort_by_column = augment_data["matched_column"]

                augment_sql_prompt = generate_augmented_sql_prompt(
                    input_cols=input_table.columns,
                    datalake_table_name=datalake_table_name,
                    join_key_input=input_table_key,
                    join_key_datalake=datalake_table_key,
                    sort_col=sort_by_column
                )

                augment_sql_query = call_gpt(augment_sql_prompt).strip()

                if augment_sql_query:
                    st.markdown("### Augmented SQL Query")
                    st.code(augment_sql_query, language="sql")

                    # Register both tables
                    con.register(datalake_table_name, st.session_state.data_lake[datalake_table_name])
                    augment_result_df = con.execute(augment_sql_query).df()
                    st.dataframe(augment_result_df)
                else:
                    st.error("⚠️ Could not generate SQL. Try again.")
