import os
from pathlib import Path
import base64
import streamlit as st
import pandas as pd
import duckdb
import cli_only
from algorithms.index_builder import build_indexes_from_datalake, load_indexes
from algorithms.join_discovery import discover_join
from algorithms import semantic_type_extractor, minhash_builder, table_description_builder

os.environ["TOKENIZERS_PARALLELISM"] = "false"

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

semantic_distance_threshold_for_datalake_column_mapping = 0.4
cosine_distance_threshold_for_existing_column_mapping = 0.2
min_joinability_distance_threshold = 0.99

suggestion_deduplication_semantic_type_distance_threshold_dict = {
    "country_datalake": 0.1,
    "employee_datalake": 0,
    "mitdwh_datalake": 0.3
}

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

# ───────────────────── State reset helpers ──────────────────────────────────
def _reset_common_state():
    """Reset transient UI/results state so a new selection starts fresh."""
    # Suggestion & augmentation artifacts
    st.session_state.suggestions_df = None
    st.session_state.sorting_suggestions = {}
    st.session_state.augmentation_cache = {}
    # Selection & visibility
    st.session_state.confirmed_sort_option = None
    st.session_state.show_sql_result = False
    # Action flags
    st.session_state.apply_sort_clicked = False
    st.session_state.augment_data_clicked = False
    st.session_state.apply_augmentation_clicked = False
    # Remove any persisted widget state for the suggestion selectbox
    if "suggestion_selectbox" in st.session_state:
        st.session_state.pop("suggestion_selectbox", None)

def reset_state_for_new_lake():
    """Reset app state when the data‑lake selection changes."""
    _reset_common_state()
    # Clear input‑table related caches
    st.session_state.uploaded_table = None
    st.session_state.uploaded_table_minhashes = None
    st.session_state.uploaded_table_semantic_type_embeddings = None
    # Clear registered relation in DuckDB (best‑effort)
    try:
        st.session_state.con.execute("DROP VIEW IF EXISTS input_table")
        st.session_state.con.execute("DROP TABLE IF EXISTS input_table")
    except Exception:
        pass

def reset_state_for_new_input_table():
    """Reset state when the input table selection changes within a lake."""
    _reset_common_state()
    # Clear input‑table specific caches; table will be reloaded right after
    st.session_state.uploaded_table_minhashes = None
    st.session_state.uploaded_table_semantic_type_embeddings = None
    # Clear any pre‑existing registration (best‑effort)
    try:
        st.session_state.con.execute("DROP VIEW IF EXISTS input_table")
        st.session_state.con.execute("DROP TABLE IF EXISTS input_table")
    except Exception:
        pass

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

from data_path import data_path

# ───────────────────── Data‑lake picker ───────────────────────────────────────
DATALAKES_ROOT = f"{data_path()}/datalakes"  # ./datalakes/datalake1/, datalake2/, …

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
        reset_state_for_new_lake()
        st.session_state.chosen_lake = chosen_lake
        st.session_state.data_lake.clear()
        st.session_state.uploaded_table = None
        st.session_state.input_table_files = []

        if chosen_lake != "<no datalakes found>":
            lake_dir   = Path(DATALAKES_ROOT) / chosen_lake
            tables_dir = lake_dir / "all_tables"
            index_dir  = lake_dir / "index_files"
            input_dir  = lake_dir / "input_tables"

            st.session_state.index_dir = index_dir 

            # 1️⃣ Read every CSV in all_tables/*
            with st.spinner(f"Loading data lake '{chosen_lake}' …"):
                build_indexes_from_datalake(
                    st.session_state.data_lake, save_dir=index_dir
                )
                st.session_state.data_lake = cli_only.load_datalake_tables(lake_dir=lake_dir)
                st.session_state.all_table_descriptions = table_description_builder.load_table_descriptions(save_dir=index_dir)
                st.session_state.all_minhashes = minhash_builder.load_minhashes(index_dir)
                st.session_state.semantic_types = semantic_type_extractor.load_semantic_types(index_dir)
                st.session_state.semantic_type_embeddings = semantic_type_extractor.load_semantic_type_embeddings(index_dir)
                st.session_state.chosen_lake = chosen_lake

            st.success("✅ Indexes built and stored in the data‑lake.")

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
        # Reset state for a new input table selection
        reset_state_for_new_input_table()
        # Find the corresponding file path
        for p in st.session_state.input_table_files:
            if p.stem == selected_input_name:
                try:
                    st.session_state.uploaded_table = pd.read_csv(p)
                    st.session_state.uploaded_table_minhashes = minhash_builder.build_minhashes(
                        datalake={"input_table": st.session_state.uploaded_table}, parallel_enabled=False
                    )["input_table"]
                    st.session_state.uploaded_table_semantic_type_embeddings = semantic_type_extractor.build_semantic_type_embeddings(
                        st.session_state.uploaded_table
                    )
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
    input_df = st.session_state.uploaded_table

    if st.button("Get Suggestions 💡"):
        with st.spinner(f"Generating Suggestions …"):
            suggestions_df, augmentation_cache = cli_only.generate_numeric_column_suggestions(
                input_table=input_df,
                input_table_minhash=st.session_state.uploaded_table_minhashes,
                all_minhashes=st.session_state.all_minhashes,
                data_lake=st.session_state.data_lake,
                table_descriptions=st.session_state.all_table_descriptions,
                cosine_distance_threshold_for_existing_column_mapping=cosine_distance_threshold_for_existing_column_mapping,
                suggestion_deduplication_semantic_type_distance_threshold=suggestion_deduplication_semantic_type_distance_threshold_dict[st.session_state.chosen_lake],
                semantic_types=st.session_state.semantic_types,
                semantic_type_embeddings=st.session_state.semantic_type_embeddings,
                min_joinability_distance_threshold=min_joinability_distance_threshold
            )
            st.session_state.suggestions_df = suggestions_df
            st.session_state.augmentation_cache = augmentation_cache

# --- Display Suggestions and Selection Form ---
if st.session_state.uploaded_table is not None and st.session_state.suggestions_df is not None and not st.session_state.suggestions_df.empty:
        st.subheader("🔍 Sorting Suggestions")

        # Show suggestions with a color‑coded 'interestingness' column (0=red → 1=bright green)
        _view_cols = ['base_column', 'Augmented Column', 'interestingness', 'description']
        _df_view = st.session_state.suggestions_df[_view_cols].copy()

        def _color_interestingness(val):
            try:
                x = float(val)
            except (TypeError, ValueError):
                return ""
            # Clamp to [0,1]
            x = 0.0 if x is None else max(0.0, min(1.0, x))
            # # Linear blend: red (255,0,0) -> bright green (0,200,83)
            r = int(255 * (1.0 - x))
            g = int(200 * x)
            b = int(83 * x)
            # Lighten toward white for softer, more white-ish shades
            w = 0.6  # 0 = no lightening, 1 = fully white
            r = int(r * (1.0 - w) + 255 * w)
            g = int(g * (1.0 - w) + 255 * w)
            b = int(b * (1.0 - w) + 255 * w)
            return f"background-color: rgb({r},{g},{b});"

        _styled = _df_view.style.applymap(_color_interestingness, subset=['interestingness'])
        st.dataframe(_styled, use_container_width=True)

        input_columns = list(st.session_state.uploaded_table.columns)
        candidate_columns = list(st.session_state.suggestions_df["datalake_column"])

        # semantic_interestingness = compute_semantic_interestingness(input_columns, candidate_columns)

        # st.write(f"Semantic Utility score: {semantic_interestingness}")

        df_suggestions = st.session_state.suggestions_df

        # Generate unique readable options for user selection
        select_options = [
            f"{row['base_column']} ➝ {row['Augmented Column']}"
            for _, row in st.session_state.suggestions_df.iterrows()
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

if st.session_state.uploaded_table is not None and st.session_state.show_sql_result and st.session_state.confirmed_sort_option and st.session_state.suggestions_df is not None:


    # Find the selected row based on the confirmed option stored in session state
    # Regeberate options to find index reliably (needed because index might change)
    df_suggestions = st.session_state.suggestions_df
    current_select_options = [
        f"{row['base_column']} ➝ {row['Augmented Column']}"
        for _, row in df_suggestions.iterrows()
    ]

    # Find the index based on the confirmed option string
    selected_idx = current_select_options.index(st.session_state.confirmed_sort_option)
    selected_row = df_suggestions.iloc[selected_idx]
    sort_info = selected_row.to_dict()

    base_col = selected_row["base_column"]
    sort_attr = selected_row["datalake_column"]
    description = selected_row["description"]
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
                        '>{sort_info['Augmented Column']}</span>
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("<br>", unsafe_allow_html=True)

            interestingness = float(sort_info['interestingness'])
            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("<div style='background-color:#f9f9f9; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                st.markdown("#### Column Information")
                st.markdown(f"**Base Column:** `{sort_info['base_column']}`")
                st.markdown(f"**Required Column:** `{sort_info['Augmented Column']}`")
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                is_present = False
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
                st.markdown(f"*{sort_info['description']}*")
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
            semantic_types, semantic_type_hnsw_index, all_minhashes, all_table_descriptions = load_indexes(st.session_state.index_dir)

            row_key = (base_col, selected_row["datalake_table"], selected_row["datalake_column"])
            augment_data = st.session_state.augmentation_cache.get(row_key)
            if augment_data is None:
                st.warning(
                    "🤷‍♂️ Sorry, I couldn't find any data-lake column that can supply "
                    "the required attribute for this sort."
                )
                # nothing else to display, so skip the rest of this block
            else:
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
                                '>{augment_data['Augmented Column']}</span>
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown("<br>", unsafe_allow_html=True)

                    # Convert numpy values to Python float if needed
                    join_dist = float(augment_data['join_distance'])
                    
                    # Create two columns for the data
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.markdown("<div style='background-color:#f9f9f9; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                        st.markdown("#### 📂 Source Information")
                        st.markdown(f"**Table:** `{augment_data['datalake_table']}`")
                        st.markdown(f"**Column:** `{augment_data['datalake_column']}`")
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
                    
                    # Add action buttons at the bottom
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_btn1, col_btn2 = st.columns([1, 1])
                    
                    with col_btn1:
                        if st.button("✅ Apply Augmentation", type="primary", key="apply_aug"):
                                st.session_state.apply_augmentation_clicked = True
                    with col_btn2:
                        st.button("🔎 Preview Data", key="preview_aug")

        # proceeding with sql generation

    if st.session_state.augment_data_clicked:
        semantic_types, semantic_type_hnsw_index, minhashes, all_table_descriptions = load_indexes(st.session_state.index_dir)

        augment_data = discover_join(
            datalake_table= augment_data['datalake_table'],
            datalake_column= augment_data['datalake_column'],
            input_table_minhash= st.session_state.uploaded_table_minhashes,
            input_table_semantic_type_embeddings= st.session_state.uploaded_table_semantic_type_embeddings,
            semantic_types= st.session_state.semantic_types,
            minhashes= st.session_state.all_minhashes,
            base_col= base_col,
            min_joinability_distance_threshold= min_joinability_distance_threshold,
            cosine_distance_threshold_for_existing_column_mapping=cosine_distance_threshold_for_existing_column_mapping
        )

        

        if st.session_state.apply_augmentation_clicked:
            if augment_data is not None:
                sql, augment_result_df = cli_only.generate_augmented_sql_and_run(
                    con=con,
                    df_input=st.session_state.uploaded_table,
                    data_lake=st.session_state.data_lake,
                    augment_data=augment_data,
                    cached=True
                )
                st.markdown("### Augmented SQL Query")
                st.code(sql, language="sql")
                # Highlight the second column in bright green for quick identification
                second_col = augment_result_df.columns[1]
                styled_df = augment_result_df.style.set_properties(
                    subset=[second_col],
                    **{"background-color": "#b9f6ca"}  # bright green
                )
                st.dataframe(styled_df, use_container_width=True)

