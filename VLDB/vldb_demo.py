import streamlit as st
import pandas as pd
import sqlite3
import time
import base64
with open("insightsort_logo.png", "rb") as image_file:  # replace with your local image path
    encoded_image = base64.b64encode(image_file.read()).decode()

global_col = ''
global_source = ''

# Initialize data_lake and sorting_suggestions in st.session_state (important for reruns!)
if "data_lake" not in st.session_state:
    st.session_state.data_lake = {} 

if "sorting_suggestions" not in st.session_state:
    st.session_state.sorting_suggestions = {
"country": [
{"column": "gdp", "description": "Sort by GDP to understand the economic output of each country.  Higher GDP often correlates with higher living standards.", "interestingness": 0.85, "required_column": "gdp (in trillions USD)", "required_table": "Input table (countries)"}, 
{"column": "population", "description": "Sort by population to see the most populous countries.  Useful for understanding market size and demographic trends.", "interestingness": 0.7, "required_column": "population (in millions)", "required_table": "census_data"},
{"column": "temperature", "description": "Sort by average temperature to analyze climate patterns and potential environmental impacts.", "interestingness": 0.6, "required_column": "temperature", "required_table": "climate_metrics"},
{"column": "literacy_rate", "description": "Sort by literacy rate to assess education levels and human capital development in each country.", "interestingness": 0.75, "required_column": "literacy_rate", "required_table": "literacy_rates"},  
{"column": "life_expectancy", "description": "Sort by life expectancy to understand the average age of an individual across countries.", "interestingness": 0.80, "required_column": "life_expectancy", "required_table": "health_indicators"}, 
{"column": "inflation_rate", "description": "Sort by inflation rate to see what are the inflation rates by each country", "interestingness": 0.5, "required_column": "inflation_rate", "required_table": "economic_metrics"},
# {"column": "unemployment", "description": "Sort by unemployment rate to analyze job market conditions and economic stability.", "interestingness": 0.65, "required_column": "unemployment", "required_table": "labor_force_data"},
{"column": "gini_coefficient", "description": "Sort by Gini coefficient to understand income inequality within each country.", "interestingness": 0.7, "required_column": "gini_index", "required_table": "gini_index"}, 
{"column": "tourism", "description": "Sort by the annual number of tourists to know popularity of each country", "interestingness": 0.6, "required_column": "tourism_data", "required_table": "global_tourism"}, 
{"column": "life expectancy + literacy rate", "description": "Sort by a composite view of human development, using both life expectancy and literacy rate. Requires joining two data lake tables.", "interestingness": 0.69, "required_column": "life_expectancy, literacy_rate", "required_table": "health_indicators, literacy_rates"}, 
{"column": "gdp + healthcare expenditure", "description": "Sort by GDP first, and then by healthcare expenditures to understand how much companies invest in healthcarerelative to their gdp.", "interestingness": 0.80, "required_column": "gdp, healthcare_expenditures", "required_table": "Input table (countries), health_indicators"},


]
    }


# Streamlit app setup
st.set_page_config(page_title="InsightSort", layout="wide")
st.markdown(
    f"""
    <div style="display: inline-flex; align-items: center; justify-content: flex-start; margin-bottom: 15px; margin-top: -12px;">
        <span style="font-size: 42px; font-weight: bold;">InsightSort</span>
        <img src="data:image/png;base64,{encoded_image}" width="50" style="margin-left: 15px;" />
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown(f"""<p style="font-weight: 600; font-size: 1.1rem;">Discover meaningful ways to sort your tables!</p>""",  unsafe_allow_html=True)
st.markdown(f"""<p style="font-size: 1rem; margin-top: -10px;">InsightSort helps you explore your data by recommending smart, semantically interesting attributes to sort by — even if those attributes aren’t in your original table.</p>""",  unsafe_allow_html=True)



# st.sidebar.title("InsightSort")
st.sidebar.markdown(
    f"""
    <div style="display: inline-flex; align-items: center; justify-content: flex-start; margin-top: 20px">
        <span style="font-size: 24px; font-weight: bold;">InsightSort</span>
        <img src="data:image/png;base64,{encoded_image}" width="30" style="margin-left: 10px;" />
    </div>
    """,
    unsafe_allow_html=True
)
st.sidebar.header("📂 Upload Files")
uploaded_file = st.sidebar.file_uploader("⬆️ Upload Input Table (CSV)", type=["csv"])
st.sidebar.markdown("This is your starting point — we'll help you sort it better by suggesting insightful attributes to sort on.")


if "uploaded_table" not in st.session_state:
    st.session_state.uploaded_table = None  # Initialize to None

if uploaded_file:
    st.session_state.uploaded_table = pd.read_csv(uploaded_file)
    st.subheader("Input Table:")
    st.dataframe(st.session_state.uploaded_table)

datalake_files = st.sidebar.file_uploader("⬆️ Upload Data Lake CSVs", type=["csv"], accept_multiple_files=True)
st.sidebar.markdown("InsightSort will scan these tables for useful attributes that can be joined with your input table to enhance sorting.")

if datalake_files:
    for file in datalake_files:
        df = pd.read_csv(file)
        st.session_state.data_lake[file.name.replace(".csv", "")] = df

# Display Data Lake Tables
if "data_lake" in st.session_state and st.session_state.data_lake:  # Check if data_lake exists and is not empty
    st.subheader("Data Lake Tables 📚")
    table_names = list(st.session_state.data_lake.keys())

    selected_table_index = st.selectbox("Select a table to view it here: ", range(len(table_names)),
                                        format_func=lambda x: table_names[x])

    if selected_table_index is not None:
        selected_table = table_names[selected_table_index]
        st.write(f"{selected_table} Table")
        st.dataframe(st.session_state.data_lake[selected_table])
    else:
        st.write("Select a table to display it here.")

# Attribute selection for sorting
if st.session_state.uploaded_table is not None:
    attributes = ["None"] + st.session_state.uploaded_table.columns.tolist()
    selected_attribute = st.selectbox("Select a column from input table (countries) to generate sort suggestions:", attributes)
    # st.session_state.max_suggestions = st.selectbox("Max number of sort suggestions: ⚙️", tuple(range(1, 11)))
    col1, col2 = st.columns([1, 3])  # Adjust width ratio as needed
    with col1:
        st.session_state.max_suggestions = st.slider("⚙️ Max suggestions:", 1, 10, 1, format="%d")


    if st.button("Get Suggestions 💡"):
        with st.spinner("Generating sorting suggestions... ⏳"):
            time.sleep(2)
            suggestion_data = []
            if selected_attribute in st.session_state.sorting_suggestions:
                for suggestion in st.session_state.sorting_suggestions[selected_attribute]:
                    column = suggestion["column"]
                    description = suggestion["description"]
                    interestingness = suggestion["interestingness"]
                    required_column = suggestion["required_column"]
                    required_table = suggestion["required_table"]

                    is_available = column in st.session_state.uploaded_table.columns
                    source = "Available" if is_available else required_table

                    suggestion_data.append({
                        "Suggestion Name": column,
                        "Description": description,
                        "Interestingness": interestingness,
                        "Required Column(s)": required_column,
                        "Required Table(s)": required_table if required_table else "None",
                        "Column available in the input table": "Yes" if required_table is "Input table (countries)" else "No"
                    })

                suggestions_df = pd.DataFrame(suggestion_data)
                suggestions_df = suggestions_df.sort_values(by=["Interestingness"], ascending=False)
                st.session_state.suggestions_df = suggestions_df

            else:
                st.warning(f"No sorting suggestions found for attribute: {selected_attribute}")
            

    # Display Suggestion Details (separate block to ensure it runs after suggestion generation)
    if "suggestions_df" in st.session_state and not st.session_state.suggestions_df.empty:
        def color_available(val):
            color = 'lightgreen' if val == 'Yes' else 'lightyellow'
            return f'background-color: {color}'

        styled_suggestions_df = st.session_state.suggestions_df.head(st.session_state.max_suggestions).style.applymap(color_available, subset=['Column available in the input table'])

        st.subheader("Sort Suggestions generated by the LLM:")
        st.markdown("**Here are some recommended attributes to sort your table in interesting ways.**")
        st.table(styled_suggestions_df)
        selected_suggestion = st.selectbox("Select a sort suggestion for details:",
                                            st.session_state.suggestions_df.head(st.session_state.max_suggestions)["Suggestion Name"].tolist())

        selected_suggestion_details = st.session_state.suggestions_df[
            st.session_state.suggestions_df["Suggestion Name"] == selected_suggestion]

        if not selected_suggestion_details.empty:
            st.subheader("Suggestion Details 🔍")
            st.write(f"**Sort By:** {selected_suggestion_details.iloc[0]['Suggestion Name']}")
            st.write(f"**Description:** {selected_suggestion_details.iloc[0]['Description']}")
            st.write(f"**Interestingness:** {selected_suggestion_details.iloc[0]['Interestingness']}")
            st.write(
                f"**Required Column(s):** {selected_suggestion_details.iloc[0]['Required Column(s)'] if selected_suggestion_details.iloc[0]['Required Column(s)'] else 'None'}")
            st.write(
                f"**Required Table(s):** {selected_suggestion_details.iloc[0]['Required Table(s)'] if selected_suggestion_details.iloc[0]['Required Table(s)'] else 'None'}")

            selected_source = selected_suggestion_details.iloc[0]['Required Table(s)']

            if selected_source == "Input table (countries)":
                st.markdown(
                    f'<div style="background-color:#D4EDDA; color:#0F5132; padding:10px; border-radius:5px; margin-bottom: 10px;">Sort by {selected_suggestion} (Column present in uploaded table) ✅</div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div style="background-color:#E0E0E0; padding:10px; border-radius:5px; margin-bottom: 10px;">Sort by {selected_suggestion} (Needs to fetch from {selected_source} table) ⚠️</div>',
                    unsafe_allow_html=True)  # use selected_source
                if "data_lake" in st.session_state and selected_source in st.session_state.data_lake:  # use st.session_state.data_lake here and check that the key exists!
                    input_table = st.session_state.uploaded_table
                    source_table = st.session_state.data_lake[selected_source]  # Access data_lake through st.session_state

                    # common join key (assuming it's 'country')
                    join_key = "country"

                    # Function to generate a styled DataFrame
                    def highlight_join_key(df, key):
                        def style_row(row):
                            if row.name in df.index:
                                return ['background-color: lightgreen' if col == key else '' for col in row.index]
                            else:
                                return ['' for col in row.index]  # Default style for the rest

                        return df.style.apply(style_row, axis=1)

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("Input Table")
                        styled_input_table = highlight_join_key(input_table.head(), join_key)
                        st.dataframe(styled_input_table)
                    with col2:
                        st.write(f"{selected_source} Table")  # use selected_source
                        styled_source_table = highlight_join_key(source_table.head(), join_key)
                        st.dataframe(styled_source_table)

                    

                    try:
                        source_subset = source_table[[join_key, selected_suggestion]]
                        joined_table = input_table.merge(source_subset, on=join_key, how="left")

                        # Function to highlight the target column
                        def highlight_target_col(df, target_column):
                            def style_row(row):
                                return ['background-color: lightblue' if col == target_column else '' for col in row.index]

                            return df.style.apply(style_row, axis=1)

                        # Display preview with the target column highlighted
                        # st.write("Joined Table Preview (First 2 rows):")
                        st.markdown("**Here’s what your input table looks like when enriched with new data (First 10 rows preview).**  \nWe’ve joined it with the relevant data lake table to bring in the sorting column you selected — take a look at the result.")

                        styled_joined_table = highlight_target_col(joined_table.head(10),
                                                                    selected_suggestion)  # use selected_suggestion
                        st.dataframe(styled_joined_table)

                        st.markdown("""
                    <style>
                    .legend-container {
                        display: flex;
                        align-items: center;
                        margin-bottom: 10px;
                    }
                    .legend-color {
                        width: 20px;
                        height: 20px;
                        border-radius: 50%; /* Make it a circle */
                        margin-right: 10px;
                        display: inline-block; /* Ensure proper spacing */
                    }
                    .legend-text {
                        font-size: 14px;
                    }
                    </style>

                    **Understanding Table Highlights:**

                    <div class="legend-container">
                        <span class="legend-color" style="background-color: lightgreen;"></span>
                        <span class="legend-text">Join Key (Country)</span>
                    </div>

                    <div class="legend-container">
                        <span class="legend-color" style="background-color: lightblue;"></span>
                        <span class="legend-text">Target Column to Sort By</span>
                    </div>

                    """, unsafe_allow_html=True)

                    except Exception as e:
                        st.error(f"Error creating joined table preview: {e}")
                
            if st.button(f"Generate SQL Query for {selected_suggestion}",
                         help="Click to generate the SQL query"):
                
                with st.spinner("Generating sql query... ⏳"):
                    time.sleep(2)
                    selected_suggestion_column = selected_suggestion_details.iloc[0]['Required Column(s)']
                    selected_suggestion_table = selected_suggestion_details.iloc[0]['Required Table(s)']

                    if selected_source == "Input table (countries)":

                        if "gdp" in selected_suggestion_column:
                            sql_query = f"""SELECT * FROM countries ORDER BY "gdp (in trillions USD)" DESC;"""
                        else:
                            sql_query = f"SELECT * FROM countries ORDER BY {selected_suggestion_column} DESC;"
                        st.session_state.generated_query = sql_query
                        # removed breaks to go through all suggestions if there are more than one
                        st.session_state.global_source = "Input table (countries)"
                        st.session_state.global_col = selected_suggestion_column
        
                    else:
                        # selected_source == selected_suggestion_table
                        if "population" in selected_suggestion_column:
                            sql_query = f"""SELECT A.*, B."population (in millions)" FROM countries A
LEFT JOIN census_data B ON A.country = B.country
ORDER BY B."population (in millions)" DESC;"""
                        else:
                            sql_query = f"""SELECT A.*, B.{selected_suggestion_column} FROM countries A
LEFT JOIN {selected_source} B ON A.country = B.country
ORDER BY B.{selected_suggestion} DESC;"""  # use selected_source and selected_suggestion
                        st.session_state.generated_query = sql_query
                        st.session_state.global_source = selected_source
                        st.session_state.global_col = selected_suggestion_column

            
                    st.rerun() 


if "generated_query" in st.session_state:
    st.session_state.current_page = "sql_query"
    st.subheader("Generated SQL Query 📜")
    st.markdown(f"```sql\n{st.session_state.generated_query}\n```")
    def highlight_target_col(df, target_column):
        def style_row(row):
            return ['background-color: lightblue' if col == target_column else '' for col in row.index]

        return df.style.apply(style_row, axis=1)
    with st.spinner("Executing sql query... ⏳"):
        time.sleep(1)
        if st.session_state.global_source == "Input table (countries)":
            sorted_table = st.session_state.uploaded_table.sort_values(by=st.session_state.global_col, ascending=False).reset_index(drop=True)
            sorted_table.index += 1
            highlighted_sorted_table = highlight_target_col(sorted_table, st.session_state.global_col)
            st.subheader("Sorted Table")
            st.dataframe(highlighted_sorted_table)
        else:
            if st.session_state.global_source in st.session_state.data_lake.keys():
                source_subset = st.session_state.data_lake[st.session_state.global_source][["country", st.session_state.global_col]]
                joined_table = st.session_state.uploaded_table.merge(source_subset, on="country", how="left")
                sorted_table = joined_table.sort_values(by=st.session_state.global_col, ascending=False).reset_index(drop=True)

                sorted_table.index += 1
                highlighted_sorted_table = highlight_target_col(sorted_table, st.session_state.global_col)
                st.subheader("Sorted Table")
                st.dataframe(highlighted_sorted_table)
