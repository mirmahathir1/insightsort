import streamlit as st
import pandas as pd
import sqlite3
import time
import networkx as nx
import matplotlib.pyplot as plt



global_col = ''
global_source = ''
# Sample data lake with 10 tables
# data_lake = {
#     "population": pd.DataFrame({"country": ["USA", "India", "Germany"], "population": [331000000, 1380000000, 83000000]}),
#     "temperature": pd.DataFrame({"country": ["USA", "India", "Germany"], "avg_temperature": [13.0, 25.5, 10.5]}),
#     "literacy_rate": pd.DataFrame({"country": ["USA", "India", "Germany", "China", "Japan"], "literacy_rate": [99, 74, 99, 97, 99]}),
#     "life_expectancy": pd.DataFrame({"country": ["USA", "India", "Germany"], "life_expectancy": [78.5, 69.7, 81.1]}),
#     "inflation": pd.DataFrame({"country": ["USA", "India", "Germany"], "inflation_rate": [1.5, 5.0, 1.3]}),
#     "continent_mapping": pd.DataFrame({"country": ["USA", "India", "Germany"], "continent": ["North America", "Asia", "Europe"]}),
#     "unemployment": pd.DataFrame({"country": ["USA", "India", "Germany"], "unemployment_rate": [4.5, 7.1, 3.8]}),
#     "gini_index": pd.DataFrame({"country": ["USA", "India", "Germany"], "gini_coefficient": [41.4, 35.7, 31.1]}),
#     "tourism": pd.DataFrame({"country": ["USA", "India", "Germany"], "annual_tourists": [80000000, 17000000, 39000000]}),
#     "currency": pd.DataFrame({"country": ["USA", "India", "Germany"], "currency_name": ["USD", "INR", "EUR"]}),
# }

data_lake = {}

# Predefined sorting suggestions
# sorting_suggestions = {
#     "country": ["gdp", "population", "temperature", "literacy_rate", "life_expectancy", "inflation", "unemployment", "gini_coefficient", "tourism"],
#     "job_level": ["seniority_order"],
#     "company": ["market_cap", "revenue", "number_of_employees"],
#     "product": ["price", "popularity", "ratings"],
#     "continent": ["avg_gdp", "avg_population", "avg_temperature"]
# }


sorting_suggestions = {
    "country": [
        {"column": "gdp", "description": "Sort by GDP to understand the economic output of each country.  Higher GDP often correlates with higher living standards.", "interestingness": 0.8, "required_table": "gdp_data"},  # Replace 'gdp_data' with actual table name
        {"column": "population", "description": "Sort by population to see the most populous countries.  Useful for understanding market size and demographic trends.", "interestingness": 0.7, "required_table": None},
        {"column": "temperature", "description": "Sort by average temperature to analyze climate patterns and potential environmental impacts.", "interestingness": 0.6, "required_table": "temperature_data"}, # Replace 'temperature_data' with actual table name
        {"column": "literacy_rate", "description": "Sort by literacy rate to assess education levels and human capital development in each country.", "interestingness": 0.75, "required_table": "literacy_data"},  # Replace 'literacy_data' with actual table name
        {"column": "life_expectancy", "description": "Sort by life expectancy to understand health and well-being indicators across countries.", "interestingness": 0.85, "required_table": "life_expectancy_data"}, # Replace 'life_expectancy_data' with actual table name
        {"column": "inflation", "description": "Sort by inflation rate to see what are the inflation rates by each country", "interestingness": 0.5, "required_table": "inflation_data"}, # Replace 'inflation_data' with actual table name
        {"column": "unemployment", "description": "Sort by unemployment rate to analyze job market conditions and economic stability.", "interestingness": 0.65, "required_table": "unemployment_data"}, # Replace 'unemployment_data' with actual table name
        {"column": "gini_coefficient", "description": "Sort by Gini coefficient to understand income inequality within each country.", "interestingness": 0.7, "required_table": "gini_data"}, # Replace 'gini_data' with actual table name
        {"column": "tourism", "description": "Sort by the annual number of tourists to know popularity of each country", "interestingness": 0.6, "required_table": "tourism_data"}, # Replace 'tourism_data' with actual table name

    ]
}


# Streamlit app setup
st.set_page_config(page_title="Semantic Sort App", layout="wide")
st.title("Semantic Sorting System")

st.sidebar.header("📂 Upload Files")
# st.markdown("""
# <style>
# div.stButton > button:nth-child(1) {
#     background-color: #ADD8E6;
#     color: black;
#     border: none;
#     border-radius: 5px;
#     padding: 0.5em 1em;
#     font-weight: bold;
# }
# </style>
# """, unsafe_allow_html=True)
uploaded_file = st.sidebar.file_uploader("⬆️ Upload Input Table (CSV)", type=["csv"])
if uploaded_file:
    st.session_state.uploaded_table = pd.read_csv(uploaded_file)
    st.subheader("Uploaded Table: ✅")
    st.dataframe(st.session_state.uploaded_table)

datalake_files = st.sidebar.file_uploader("⬆️ Upload Data Lake CSVs", type=["csv"], accept_multiple_files=True)
if datalake_files:
    for file in datalake_files:
        df = pd.read_csv(file)
        data_lake[file.name.replace(".csv", "")] = df

# if data_lake:
#     st.subheader("Data Lake Tables 📚")
#     tab_names = list(data_lake.keys())
#     tabs = st.tabs(tab_names)  # Create tabs with table names
#     for index, tab_name in enumerate(tab_names):
#         with tabs[index]:
#             # st.write(f"**{tab_name} Table**") # Optional: Add table name as header in tab
#             st.dataframe(data_lake[tab_name])

if data_lake:
    st.subheader("Data Lake Tables 📚")
    table_names = list(data_lake.keys())

    selected_table_index = st.selectbox("Select a table: ", range(len(table_names)), format_func=lambda x: table_names[x])

    if selected_table_index is not None:
        selected_table = table_names[selected_table_index]
        st.write(f"{selected_table} Table")
        st.dataframe(data_lake[selected_table])
    else:
        st.write("Select a table to display it here.")


# Attribute selection for sorting
if "uploaded_table" in st.session_state and st.session_state.uploaded_table is not None:
    attributes = st.session_state.uploaded_table.columns.tolist()
    selected_attribute = st.selectbox("Select an attribute to generate sort suggestions:", attributes)
    # max_suggestions = st.slider("Max number of sort suggestions", 1, 5, 3)
    max_suggestions = st.selectbox("Max number of sort suggestions: ⚙️", tuple(range(1, 6)))

    if st.button("Get Suggestions 💡"):
        with st.spinner("Generating sorting suggestions... ⏳"):
            suggestion_data = []
            if selected_attribute in sorting_suggestions:
                for suggestion in sorting_suggestions[selected_attribute]:
                    column = suggestion["column"]
                    description = suggestion["description"]
                    interestingness = suggestion["interestingness"]
                    required_table = suggestion["required_table"]

                    # Check if the column is available in the uploaded table
                    is_available = column in st.session_state.uploaded_table.columns

                    suggestion_data.append({
                        "Sort Suggestion": column,
                        "Description": description,
                        "Interestingness": interestingness,
                        "Required Table": required_table if required_table else "None",
                        "Available": "Yes" if is_available else "No"
                    })


                # Create the sort suggestions DataFrame
                suggestions_df = pd.DataFrame(suggestion_data)

                # Function to color the "Available" column
                def color_available(val):
                    color = 'green' if val == 'Yes' else 'lightgray'
                    return f'background-color: {color}'

                # Apply the styling to the DataFrame
                styled_suggestions_df = suggestions_df.style.applymap(color_available, subset=['Available'])
                st.subheader("Sort Suggestions ℹ️")
                st.dataframe(styled_suggestions_df, use_container_width=True)

                selected_suggestion = st.selectbox("Select a sort suggestion for details:", suggestions_df["Sort Suggestion"].tolist())

                if selected_suggestion:
                    

            st.session_state.sort_suggestions = suggestion_data
            st.rerun()

       




# Display sort suggestions on a new page
if "sort_suggestions" in st.session_state and st.session_state.sort_suggestions:
    st.session_state.current_page = "sort_suggestions"
    st.subheader("Sort Suggestions ℹ️")
    for col, source in st.session_state.sort_suggestions[:max_suggestions]:
        if source == "Available":
            st.markdown(f'<div style="background-color:#D4EDDA; color:#0F5132; padding:10px; border-radius:5px; margin-bottom: 10px;">Sort by {col} (Column present in uploaded table) ✅</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="background-color:#E0E0E0; padding:10px; border-radius:5px; margin-bottom: 10px;">Sort by {col} (Needs to fetch from {source}) ⚠️</div>', unsafe_allow_html=True)
            # if source in data_lake:
            #     G = nx.Graph()
            #     G.add_node("Input", color='lightblue') 
            #     G.add_node(source, color='lightgreen') 
            #     G.add_edge("Input", source, label="Join: country") 

            #     fig, ax = plt.subplots(figsize=(1.5, 0.8), dpi=60)  #

            #     pos = {"Input": [-0.5, 0], source: [0.5, 0]}
            #     node_colors = ['lightblue' if node == 'Input' else 'lightgreen' for node in G.nodes()]

            #     nx.draw(G, pos,
            #             with_labels=True,
            #             node_color=node_colors,
            #             edgecolors='black',
            #             linewidths=0.2,      
            #             node_size=500,      
            #             font_size=4,      
            #             width=0.3,         
            #             alpha=0.6,           
            #             edge_color='gray',
            #             ax=ax)

            #     edge_labels = nx.get_edge_attributes(G, 'label')
            #     nx.draw_networkx_edge_labels(G, pos,
            #                                 edge_labels=edge_labels,
            #                                 font_size=5,    
            #                                 ax=ax)

            #     ax.set_xlim([-0.8, 0.8]) 
            #     ax.set_ylim([-0.3, 0.3]) 
            #     ax.axis('off') 
            #     plt.tight_layout(pad=0.1)

            #     st.pyplot(fig)  
            #     plt.close(fig)

            if source in data_lake:
                input_table = st.session_state.uploaded_table
                source_table = data_lake[source]

                # Find the common join key (assuming it's 'country')
                join_key = "country"

                # Create a function to generate a styled DataFrame
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
                    st.write(f"{source} Table")
                    styled_source_table = highlight_join_key(source_table.head(), join_key)
                    st.dataframe(styled_source_table)

                try:
                    joined_table = input_table.merge(source_table, on=join_key, how="left")

                    # Function to highlight the target column
                    def highlight_target_col(df, target_column):
                        def style_row(row):
                            return ['background-color: lightcoral' if col == target_column else '' for col in row.index]
                        return df.style.apply(style_row, axis=1)

                    # Display preview with the target column highlighted
                    st.write("Joined Table Preview (First 2 rows):")
                    styled_joined_table = highlight_target_col(joined_table.head(2), col) # `col` is the column to be sorted by
                    st.dataframe(styled_joined_table)

                except Exception as e:
                    st.error(f"Error creating joined table preview: {e}")

        if st.button(f"Generate SQL Query for {col}", help="Click to generate the SQL query"):

            if source != "Available":
                with st.spinner("Finding table to join on... 🔍"):
                    time.sleep(2)
                with st.spinner("Joining tables... 🔗"):
                    time.sleep(2)
            if source == "Available":
                sql_query = f"SELECT * FROM uploaded_table ORDER BY {col} ASC;"
                global_col = col
                global_source = source
                st.session_state.generated_query = sql_query
                break
            else:
                sql_query = f"SELECT A.*, B.{col} FROM uploaded_table A JOIN {source} B ON A.country = B.country ORDER BY B.{col} DESC;"
                global_col = col
                global_source = source
                st.session_state.generated_query = sql_query
                break
            
            # break
            st.rerun()

if "generated_query" in st.session_state:
    st.session_state.current_page = "sql_query"
    st.subheader("Generated SQL Query 📜")
    st.code(st.session_state.generated_query, language="sql")
    # Display sorted table
    if 'uploaded_table' in st.session_state:
        if global_source == "Available":
            sorted_table = st.session_state.uploaded_table.sort_values(by=global_col)
        else:
            if global_source in data_lake.keys():
                joined_table = st.session_state.uploaded_table.merge(data_lake[global_source], on="country", how="left")
                sorted_table = joined_table.sort_values(by=global_col, ascending=False)
        st.subheader("Sorted Table")
        st.dataframe(sorted_table)
    
    # # Display sorted table
    # if 'uploaded_table' in st.session_state:
    #     if "ORDER BY" in st.session_state.generated_query:
    #         sorted_table = st.session_state.uploaded_table.sort_values(by=global_col)
    #         st.subheader("Sorted Table")
    #         st.dataframe(sorted_table)


# import streamlit as st
# import pandas as pd
# import time
# import numpy as np

# Sample data lake (replace with your actual data lake loading)
data_lake = {}

# Predefined sorting suggestions with descriptions and interestingness scores
sorting_suggestions = {
    "country": [
        {"column": "gdp", "description": "Sort by GDP to understand the economic output of each country.  Higher GDP often correlates with higher living standards.", "interestingness": 0.8, "required_table": "gdp_data"},  # Replace 'gdp_data' with actual table name
        {"column": "population", "description": "Sort by population to see the most populous countries.  Useful for understanding market size and demographic trends.", "interestingness": 0.7, "required_table": None},
        {"column": "temperature", "description": "Sort by average temperature to analyze climate patterns and potential environmental impacts.", "interestingness": 0.6, "required_table": "temperature_data"}, # Replace 'temperature_data' with actual table name
        {"column": "literacy_rate", "description": "Sort by literacy rate to assess education levels and human capital development in each country.", "interestingness": 0.75, "required_table": "literacy_data"},  # Replace 'literacy_data' with actual table name
        {"column": "life_expectancy", "description": "Sort by life expectancy to understand health and well-being indicators across countries.", "interestingness": 0.85, "required_table": "life_expectancy_data"}, # Replace 'life_expectancy_data' with actual table name
        {"column": "inflation", "description": "Sort by inflation rate to see what are the inflation rates by each country", "interestingness": 0.5, "required_table": "inflation_data"}, # Replace 'inflation_data' with actual table name
        {"column": "unemployment", "description": "Sort by unemployment rate to analyze job market conditions and economic stability.", "interestingness": 0.65, "required_table": "unemployment_data"}, # Replace 'unemployment_data' with actual table name
        {"column": "gini_coefficient", "description": "Sort by Gini coefficient to understand income inequality within each country.", "interestingness": 0.7, "required_table": "gini_data"}, # Replace 'gini_data' with actual table name
        {"column": "tourism", "description": "Sort by the annual number of tourists to know popularity of each country", "interestingness": 0.6, "required_table": "tourism_data"}, # Replace 'tourism_data' with actual table name

    ]
}

st.set_page_config(page_title="Semantic Sort App", layout="wide")
st.title("Semantic Sorting System")

st.sidebar.header("📂 Upload Files")

# Uploading input file in the sidebar
uploaded_file = st.sidebar.file_uploader("⬆️ Upload Input Table (CSV)", type=["csv"])
if uploaded_file:
    st.session_state.uploaded_table = pd.read_csv(uploaded_file)
    st.subheader("Uploaded Table: ✅")
    st.dataframe(st.session_state.uploaded_table)

# Uploading Data Lake Tables
datalake_files = st.sidebar.file_uploader("⬆️ Upload Data Lake CSVs", type=["csv"], accept_multiple_files=True)
if datalake_files:
    for file in datalake_files:
        df = pd.read_csv(file)
        data_lake[file.name.replace(".csv", "")] = df

if data_lake:
    st.subheader("Data Lake Tables 📚")
    table_names = list(data_lake.keys())

    # Display the table name selection
    selected_table_index = st.selectbox("Select a table:", range(len(table_names)), format_func=lambda x: table_names[x])

    # Display the selected table below the selection
    if selected_table_index is not None:
        selected_table = table_names[selected_table_index]
        st.write(f"**{selected_table} Table**")
        st.dataframe(data_lake[selected_table])
    else:
        st.write("Select a table to display it here.")

if "uploaded_table" in st.session_state and st.session_state.uploaded_table is not None:
    selected_attribute = "country"  # Hardcoded to "country"

    # Prepare data for the sort suggestions table
    suggestion_data = []
    for suggestion in sorting_suggestions[selected_attribute]:
        column = suggestion["column"]
        description = suggestion["description"]
        interestingness = suggestion["interestingness"]
        required_table = suggestion["required_table"]

        # Check if the column is available in the uploaded table
        is_available = column in st.session_state.uploaded_table.columns

        suggestion_data.append({
            "Sort Suggestion": column,
            "Description": description,
            "Interestingness": interestingness,
            "Required Table": required_table if required_table else "None",
            "Available": "Yes" if is_available else "No"
        })

    # Create the sort suggestions DataFrame
    suggestions_df = pd.DataFrame(suggestion_data)

    # Function to color the "Available" column
    def color_available(val):
        color = 'green' if val == 'Yes' else 'lightgray'
        return f'background-color: {color}'

    # Apply the styling to the DataFrame
    styled_suggestions_df = suggestions_df.style.applymap(color_available, subset=['Available'])
    st.subheader("Sort Suggestions ℹ️")
    st.dataframe(styled_suggestions_df, use_container_width=True)

    # Handle selection
    selected_suggestion = st.selectbox("Select a sort suggestion for details:", suggestions_df["Sort Suggestion"].tolist())

    # Display details based on the selection
    if selected_suggestion:
        selected_suggestion_data = next(item for item in sorting_suggestions[selected_attribute] if item["column"] == selected_suggestion)
        col = selected_suggestion_data["column"]
        source = next((table_name for table_name, df in data_lake.items() if selected_suggestion_data["required_table"] is not None and selected_suggestion_data["required_table"] in table_name ), None) #Find the datalake table matching the required_table
        if source: #The source is the data lake table we want to join on.
            st.write(f"You selected: {selected_suggestion}")
            input_table = st.session_state.uploaded_table
            source_table = data_lake[table_names[selected_table_index]] #data_lake[source]

            # Find the common join key (assuming it's 'country')
            join_key = "country"

            # Create a function to generate a styled DataFrame
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
                st.write(f"{source} Table")
                styled_source_table = highlight_join_key(source_table.head(), join_key)
                st.dataframe(styled_source_table)

            try:
                joined_table = input_table.merge(source_table, on=join_key, how="left")

                # Function to highlight the target column
                def highlight_target_col(df, target_column):
                    def style_row(row):
                        return ['background-color: lightcoral' if col == target_column else '' for col in row.index]
                    return df.style.apply(style_row, axis=1)

                # Display preview with the target column highlighted
                st.write("Joined Table Preview (First 2 rows):")
                styled_joined_table = highlight_target_col(joined_table.head(2), col) # `col` is the column to be sorted by
                st.dataframe(styled_joined_table)

            except Exception as e:
                st.error(f"Error creating joined table preview: {e}")
        else:
            st.write(f"You selected: {selected_suggestion}")
            input_table = st.session_state.uploaded_table
            st.dataframe(input_table)
            # try:
            #     joined_table = input_table.merge(source_table, on=join_key, how="left")

            #     # Function to highlight the target column
            #     def highlight_target_col(df, target_column):
            #         def style_row(row):
            #             return ['background-color: lightcoral' if col == target_column else '' for col in row.index]
            #         return df.style.apply(style_row, axis=1)

            #     # Display preview with the target column highlighted
            #     st.write("Joined Table Preview (First 2 rows):")
            #     styled_joined_table = highlight_target_col(joined_table.head(2), col) # `col` is the column to be sorted by
            #     st.dataframe(styled_joined_table)

            # except Exception as e:
            #     st.error(f"Error creating joined table preview: {e}")

        # if st.button(f"Generate SQL Query for {col}", help="Click to generate the SQL query"):

        #     if source != "Available":
        #         with st.spinner("Finding table to join on... 🔍"):
        #             time.sleep(2)
        #         with st.spinner("Joining tables... 🔗"):
        #             time.sleep(2)
        #     if source == "Available":
        #         sql_query = f"SELECT * FROM uploaded_table ORDER BY {col} ASC;"
        #         global_col = col
        #         global_source = source
        #         st.session_state.generated_query = sql_query
        #         break
        #     else:
        #         sql_query = f"SELECT A.*, B.{col} FROM uploaded_table A JOIN {source} B ON A.country = B.country ORDER BY B.{col} DESC;"
        #         global_col = col
        #         global_source = source
        #         st.session_state.generated_query = sql_query
        #         break