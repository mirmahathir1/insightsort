from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pandas as pd
import openai
import re
import numpy as np
from Levenshtein import distance as levenshtein_distance
import time

openai.api_key = 'sk-proj-zvfr2IvWfqEUqsnmwIBJT3BlbkFJMxh6YiSgfcG6vEcMGJ35'  

app = Flask(__name__)
CORS(app, origins=["http://127.0.0.1:5173", "http://localhost:5173"])

def format_time(elapsed_time):
    elapsed_time = float(elapsed_time)

    if elapsed_time < 60:
        return f"{elapsed_time:.1f}s"
    else:
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        return f"{minutes}min{seconds}s"
def calculate_levenshtein_distance(list1, list2):
    f''' CALCULATES LEVENSHTEIN DISTANCE BETWEEEN TWO LISTS'''

    return levenshtein_distance(list1, list2)

def determine_semantic_sortable_columns(df, mod='4o'):
    F'''
        DETERMINE WHICH COLUMNS CAN BE USED TO SEMANTICALLY SORT THE DATASET -> OUTPUTS LIST [] OF COLUMNS
'''
    start_time = time.time()
    column_names = df.columns.tolist()
    column_values = {col: df[col].unique().tolist() for col in column_names}
    column_info = "\n".join([f"{col}: {values}" for col, values in column_values.items()])

    # prompt = f"""
    # Given a dataset with the following columns and their unique values: {column_info}, analyze and determine which columns can be semantically sorted. Semantic sorting refers to sorting columns based on the inherent meaning or contextual relationships of their values, rather than simple alphabetical or numerical order. For each column, evaluate whether its values have a natural hierarchy, contextual order, or categorical meaning or if any world knowledge can be used to sort the values of the columns. Remember, there can be multiple criterias to sort the values, even if one is present, suggest that. Examples of suitable columns include those with job levels (e.g., 'Junior', 'Mid', 'Senior'), geographic locations (e.g., 'North America', 'Europe', 'Asia'), or time-related values (e.g., 'Morning', 'Afternoon', 'Evening'). Additionally, exclude columns that contain unique identifiers, such as names, IDs, or any other primary key values that do not lend themselves to semantic ordering. Lastly, provide a list of the columns that are most suitable for semantic sorting, enclosed in square brackets, based on this analysis.
    # """'

    prompt_to_sort_values = f"Sort the values 'values' based on their semantic meaning for the column ''column_name'. Try to avoid alphabetical sorting and use context and semantic relationships. Provide the values and explain the sorting criteria. Give the best possible and most relevant criteria to sort the value and provide the full explanation of the sorting criteria for sure. Add 2 lines after every suggestion in the output."


    prompt = f"""
    Given a dataset with the following columns and their unique values: {column_info}, analyze and determine which columns can be semantically sorted. Semantic sorting refers to sorting columns based on the inherent meaning or contextual relationships of their values, rather than simple alphabetical or numerical order. For each column, evaluate whether its values have a natural hierarchy, contextual order, or categorical meaning or if any world knowledge can be used to sort the values of the columns. Remember, there can be multiple criterias to sort the values, even if one is present, suggest that. Examples of suitable columns include those with job levels (e.g., 'Junior', 'Mid', 'Senior'), geographic locations (e.g., 'North America', 'Europe', 'Asia'), or time-related values (e.g., 'Morning', 'Afternoon', 'Evening'). Additionally, exclude columns that contain unique identifiers, such as names, IDs, or any other primary key values that do not lend themselves to semantic ordering. Lastly, provide a list of the columns that are most suitable for semantic sorting, enclosed in square brackets, based on this analysis.
Consider world knowledge about the column and its values, which values are considered superior and which inferiro and provide suggestions. Give all the suggestions possible, even if there is not a universally accepted sorting order but consider the world knowledge about the column values, thier importance, how they are perceived, etc.
Refer this prompt I use to semantically sort a column given its values: ${prompt_to_sort_values}, and consider this and give the results. Try to ignore numerical columns or columns which contain dates.
After analyzing the columns, on the last line provide a list of the columns that are most suitable for semantic sorting, enclosed in square brackets [ ]. Give only the list on that line, nothing else
"""
    response = openai.ChatCompletion.create(
        model=f"gpt-{mod}",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0.7
    )

    result = response.choices[0].message['content']
    end_time = time.time()
    elapsed_time = format_time(end_time - start_time)
    return result, elapsed_time


def determine_semantic_sortable_column_pairs(df, mod='4o'):

    F'''DETERMINE WHICH COLUMN PAIRS CAN BE USED TO SEMANTICALLY SORT THE DATASET -> OUPUTS LIST [[], []] OF PAIRS'''
    start_time = time.time()
    column_names = df.columns.tolist()
    column_types = df.dtypes.to_dict()  # to identify and exclude numeric columns
    column_values = {col: df[col].unique().tolist() for col in column_names if not np.issubdtype(column_types[col], np.number)}  # excluding numeric columns
    column_info = "\n".join([f"{col}: {values}" for col, values in column_values.items()])

    prompt = f"""
    Given the dataset with the following columns and their unique values: {column_info}, analyze and determine which pairs of non-numerical columns can be semantically sorted together. Semantic sorting refers to sorting columns based on the inherent meaning or contextual relationships of their values, rather than simple alphabetical or numerical order.
    
    Ignore numerical columns (such as those containing ages, salaries, or quantities), since they can be sorted automatically. Focus only on the columns present in the dataset and exclude any hypothetical columns. Identify non-numeric column pairs that have hierarchical, contextual, or categorical relationships between their values. Exclude columns that contain primary keys, people's names, unique identifiers, or other columns that cannot be sorted semantically.

    For each pair of columns, provide detailed reasoning about why these columns can be used together for semantic sorting. Suggest at least 5 relevant column pairs, and for each suggestion, provide an explanation of the semantic or contextual relationship between the values of the two columns, ensuring they are suitable for joint sorting.

    Provide the final list of column pairs on the last line in the format: 
    [column1, column2], [column3, column4], ...
    
    The list of pairs should be on the very last line of the response with nothing else following it. And, only the list should be present, no preceeding or succeeding words or phrases. And don't give redundant pairs. AND, GIVE ONLY THE COLUMNS WHICH ARE PRESENT< DONT GIVE RANDOM COLUMN NAMES.
    """

    response = openai.ChatCompletion.create(
        model=f"gpt-{mod}",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500,
        n=1,
        stop=None,
        temperature=0.7
    )

    result = response.choices[0].message['content']
    end_time = time.time()
    elapsed_time = format_time(end_time - start_time)
    return result, elapsed_time

    # match = re.search(r'(\[.*\])$', result.strip())
    # if match:
    #     pairs_str = match.group(1)  # Extracting the string of pairs
    #     column_pairs = [pair.strip().replace('[', '').replace(']', '').split(', ') for pair in pairs_str.split('], [')]
    #     print(column_pairs)
    # else:
    #     print("No column pairs found.")
    #     return []


def semantic_sort_column(column_name, values, constraints=None, mod="4o"):
    '''SEMANTICALLY SORTS THE COLUMN VALUES AND GIVE SUGGESTIONS'''

    start_time = time.time()
    constraints_text = f"Please follow these constraints strictly and consider this criteria only to sort, dont consider other things: {constraints}." if constraints else ""
    constraints_text = constraints_text.upper() 
    give_list_values = f"After this, lastly give a list of the sorted order values enclosed in []. List should have all the values of the column. Give only the list, nothing else. Exactly before this line, give a paragraph explaining the criteria (in detail with how the values are sorted) used to generate this sorted order. And, remember to use just one criteria to sort the elements, don't consider different criteria for different elements. And in the explanation paragraph, wrap important words between two '**'. So, last line: just a list, second last line: sorting critera, that too everything related to the explanation in the same paragraph and sentence (as i will fetch this using python by doing result[-2] i.e the second last elemnt of the result of this prompt after converting it to list by splitting result with ('\\n\\n')), no next line in the paragraph! On the next line, give sorted order list as discussed."
    prompt = f"Sort the values {values} based on their semantic meaning for the column '{column_name}. Try to avoid alphabetical sorting and use context and semantic relationships. Provide the values and explain the sorting criteria. Give the best possible and most relevant criteria to sort the value and provide the full explanation of the sorting criteria for sure. Add 2 lines after every suggestion in the output. {constraints_text}. {give_list_values}"
    print(prompt)
    # right now, it is giving one best way. to do 5:  Give 5 different ways to sort these values, each with its own explanation.
    response = openai.ChatCompletion.create(
        model=f"gpt-{mod}",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=600,
        n=1,
        stop=None,
        temperature=0.7
    )


    result = response.choices[0].message['content']
    end_time = time.time()
    elapsed_time = format_time(end_time - start_time)
    return result, elapsed_time

def sort_dataset_by_semantic_columns(df, mod='4o'):

    timings = {} # dictionary to store time taken for each step

    # step 1: function to determin which columns can be used to semantically sort the dataset
    start_time = time.time()
    result, elapsed_time = determine_semantic_sortable_columns(df, mod)
    timings["Time to find single semantic sortable columns"] = elapsed_time
    
    
    # Extracting the list of columns that are suitable for semantic sorting
    result = result.split('\n\n') 
    sort_suggestions = result[-1] 
    match = re.search(r'\[([^\[\]]*?)\]', sort_suggestions)  

    if match:
        extracted_columns_str = match.group(1)
        sortable_columns = [item.strip() for item in extracted_columns_str.split(',')]
        print(sortable_columns)
    else:
        print("No sortable columns found.")
        return {}

    sorted_datasets = {}
    row_id_orders = {}
    sorting_criteria = {}
    sorting_start_time = time.time() # start time for sorting columns

    # Iterating over each sortable column and run semantic sorting
    for column in sortable_columns:
        if column in df.columns:
            new_df = df.copy()
            if not pd.api.types.is_numeric_dtype(new_df[column]):
                unique_values = new_df[column].unique().tolist()

                column_sort_start_time = time.time()
                result, elapsed_time = semantic_sort_column(column, unique_values)
                column_sort_end_time = time.time()
                
                # timings[f"Time to sort column '{column}'"] = format_time(column_sort_end_time - column_sort_start_time)
                result = result.split('\n\n')
                
                print(result)
                sort_suggestions = result[-1] # last line
                curr_sort_criteria = result[-2] if result[-2] else [] # 2nd last line
                match = re.search(r'\[([^\[\]]*?)\]', sort_suggestions) 

                if match:
                    extracted_list_str = match.group(1)
                    extracted_list = [item.strip() for item in extracted_list_str.split(',')]

                    missing_values = [value for value in unique_values if value not in extracted_list]
                    final_categories = extracted_list + missing_values
                    
                    # Converting the column to categorical and sort the DataFrame
                    new_df[column] = pd.Categorical(new_df[column], categories=final_categories, ordered=True)
                    sorted_df = new_df.sort_values(column)
                    
                    sorted_datasets[column] = sorted_df.to_dict(orient='records')
                    row_id_orders[column] = sorted_df.index.tolist()
                    sorting_criteria[column] = curr_sort_criteria
                    # print(sorted_df)
                    # print('\n\n')
                else:
                    print(f"No sorted list found for column {column}")
        else:
            print("Suggested column not presnt in the dataset")
    
    sorting_end_time = time.time()
    timings["Time to sort dataset on all single columns"] = format_time(sorting_end_time - sorting_start_time)

    # step 3: calculate levenshtein distances
    levenshtein_start_time = time.time()
    levenshtein_results = {}
    columns = list(row_id_orders.keys())
    # print(calculate_levenshtein_distance([1, 2, 3], [1, 2, 3]))
    # print(calculate_levenshtein_distance([1, 3, 2], [1, 2, 3]))
    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            column1 = columns[i]
            column2 = columns[j]

            row_order1 = row_id_orders[column1]
            row_order2 = row_id_orders[column2]

            distance = calculate_levenshtein_distance(row_order1, row_order2)

            levenshtein_results[f"{column1} vs {column2}"] = distance

    levenshtein_end_time = time.time()
    timings["Time to calculate Levenshtein distances for single columns"] = format_time(levenshtein_end_time - levenshtein_start_time)
    return sorted_datasets, levenshtein_results, sorting_criteria, timings


def sort_dataset_by_semantic_column_pairs(df, mod='4o'):
    timings = {}  # Dictionary to store timing data

    # Step 1: Determine which column pairs can be used to semantically sort the dataset
    start_time = time.time()
    result, elapsed_time = determine_semantic_sortable_column_pairs(df, mod)
    timings["Time to find semantic sortable column pairs"] = elapsed_time


    # Step 2: Extracting the list of column pairs from the last line of the result
    result = result.split('\n\n')
    sort_suggestions = result[-1]
    # if match:
    #     extracted_columns_str = match.group(1)
    #     sortable_column_pairs = [pair.strip().replace('[', '').replace(']', '').split(', ') for pair in extracted_columns_str.split('], [')]
    #     print("Sortable Column Pairs:", sortable_column_pairs)
    # else:
    #     print("No sortable column pairs found.")
    #     return {}
    
    match = re.search(r'(\[.*\])$', sort_suggestions)
    if match:
        pairs_str = match.group(1)  # Extracting the string of pairs
        sortable_column_pairs = [pair.strip().replace('[', '').replace(']', '').split(', ') for pair in pairs_str.split('], [')]
        print(sortable_column_pairs)
    else:
        print("No column pairs found.")
        return []

    sorted_datasets = {}
    sorted_row_ids = {}
    sorting_criteria = {}
    sorting_start_time = time.time()

    # Step 3: Iterate over each sortable column pair and perform semantic sorting
    for column1, column2 in sortable_column_pairs:
        if column1 in df.columns and column2 in df.columns:
            new_df = df.copy()

            values1 = new_df[column1].tolist()
            values2 = new_df[column2].tolist()

            # Call semantic_sort_multiple_column for sorting combined values of both columns
            pair_sort_start_time = time.time()
            result, elapsed_time = semantic_sort_multiple_column(column1, values1, column2, values2)
            result = result.split('\n\n')
            pair_sort_end_time = time.time()

            # timings[f"Time to sort column pair '{column1}-{column2}'"] = format_time(pair_elapsed_time)

            curr_sorting_criteria = result[-2]
            sort_suggestions = result[-1]
            match = re.search(r'\[([^\[\]]*?)\]', sort_suggestions)

            if match:
                extracted_list_str = match.group(1)
                extracted_list = [item.strip() for item in extracted_list_str.split(',')]
                extracted_list = list(dict.fromkeys(extracted_list))

                # Create a combined column for sorting and sort the DataFrame
                new_df['combined'] = new_df[column1] + '-' + new_df[column2]
                new_df['combined'] = pd.Categorical(new_df['combined'], categories=extracted_list, ordered=True)
                sorted_df = new_df.sort_values('combined').drop(columns=['combined'])

                # Store the sorted dataset and row IDs
                sorted_datasets[f'{column1}-{column2}'] = sorted_df.to_dict(orient='records')
                sorted_row_ids[f'{column1}-{column2}'] = sorted_df.index.tolist()
                sorting_criteria[f'{column1}-{column2}'] = curr_sorting_criteria

    sorting_end_time = time.time()
    timings["Time to sort dataset on all column pairs"] = format_time(sorting_end_time - sorting_start_time)


    # Step 4: Calculate Levenshtein distances between sorted datasets based on row IDs
    levenshtein_start_time = time.time()
    levenshtein_distances = {}
    pairs = list(sorted_row_ids.keys())
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            pair_a, pair_b = pairs[i], pairs[j]
            row_ids_a, row_ids_b = sorted_row_ids[pair_a], sorted_row_ids[pair_b]

            # Calculate Levenshtein distance between the two lists of row IDs
            distance = calculate_levenshtein_distance(''.join(map(str, row_ids_a)), ''.join(map(str, row_ids_b)))
            levenshtein_distances[f'{pair_a} vs {pair_b}'] = distance

    levenshtein_end_time = time.time()
    timings["Time to calculate Levenshtein distances for column pairs"] = format_time(levenshtein_end_time - levenshtein_start_time)
    # Step 5: Return the sorted datasets and Levenshtein distances
    return sorted_datasets, levenshtein_distances, sorting_criteria, timings


def get_multiple_columns_suggestions(columns, mod='4o'):
    prompt = f"Given the columns {columns}, determine which columns can be used together to do semantic sorting of the dataset. Focus on columns that have hierarchical, contextual, or categorical relationships/values. Explicitly exclude columns that are primary keys, contain people's names, unique identifiers, or any other columns that cannot be sorted semantically. For each suggested pair of columns, provide a reasoning for their selection, ensuring they are suitable for semantic sorting and do not include primary keys or identifiers. Provide the answer in the format [column1, column2]. Explanation: reasoning about why these columns can be used together to do semantic sorting. Give as many as 5 suggestions with the most probable first."
    
    response = openai.ChatCompletion.create(
        model=f"gpt-{mod}",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0.7
    )

    return response.choices[0].message['content']

def semantic_sort_multiple_columns_all_rows(column1, values1, column2, values2, constraints=None, mod='4o'):
  '''
  Giving all rows consisting of specific columns and asking to sort them semantically.

  '''
  give_list_values = f"After this, lastly give a list of the sorted order values enclosed in []. Give only the list, nothing else."
  constraints_text = f"Please follow these constraints: {constraints}." if constraints else ""
  if len(values1) != len(values2):
        raise ValueError("The length of values1 and values2 must be the same")

  combined_values = [(v1, v2) for v1, v2 in zip(values1, values2)]

  prompt = f"""
    Given two columns '{column1}' with values {values1} and '{column2}' with values {values2}, you have specific row values from these columns. Please sort these rows semantically based on the combined values of both columns. The sorting should be contextual and consider real-world knowledge and relationships rather than simple alphabetical order.
For each row, consider how the values in '{column1}' and '{column2}' interact and influence the ranking. Explain the rationale behind the sorting criteria, detailing why certain rows are prioritized over others. Consider hierarchical, contextual, or categorical relationships, and exclude primary keys, names, or other non-semantically sortable columns. Provide the sorted rows and the reasoning behind their order as accurately and relevantly as possible.
Here are the rows: {combined_values}. {constraints_text}. {give_list_values}
"""

    # Make the API call to OpenAI
  response = openai.ChatCompletion.create(
        model=f"gpt-{mod}",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0.7
    )

  return response.choices[0].message['content']

def semantic_sort_multiple_column(column1, values1, column2, values2, constraints=None, mod='4o'):
    start_time = time.time()
    constraints_text = f"Please follow these constraints: {constraints}." if constraints else ""
    give_list_values = f"After this, lastly give a list of the sorted combined values enclosed in []. Give only the list, nothing else. Exclude duplicate values."
    prompt = f"Given the columns {column1} with values [{values1}] and {column2} with values [{values2}], provide a semantic sorting of the combined values of these columns, in the format value1-value2 for each pair. Explain the sorting criteria for the combined column, including the rationale behind why certain values come before others and what world knowledge is considered for this purpose, if any. Try to avoid alphabetical sorting and focus on context and semantic relationships. {constraints_text}. Remember to provide justification for why certain values come before others. After this, lastly give a list of the sorted order values enclosed in []. List should have all the values of the column. Give only the list, nothing else. Exactly before this line, give a paragraph explaining the criteria (in detail with how the values are sorted) used to generate this sorted order. And, remember to use just one criteria to sort the elements, don't consider different criteria for different elements. And in the explanation paragraph, wrap important words between two '**'. So, last line: just a list, second last line: sorting critera, that too everything related to the explanation in the same paragraph and sentence (as i will fetch this using python by doing result[-2] i.e the second last elemnt of the result of this prompt after converting it to list by splitting result with ('\\n\\n')), no next line in the paragraph! On the next line, give sorted order list as discussed."

    # original prompt = f"Given the columns {column1} with values [{values1}] and {column2} with values [{values2}], provide a semantic sorting of the combined values of these columns. Explain the sorting criteria for sure, for the combined column, including the rationale behind why certain values come before others and what world knowledge is considered for this purpose if any. Try to avoid alphabetical sorting and use context and semantic relationships Give the results as accurate and relevant as possible. {constraints_text}."
    response = openai.ChatCompletion.create(
        model=f"gpt-{mod}",
        messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
        max_tokens=700,
        n=1,
        stop=None,
        temperature=0.7
    )

    result = response.choices[0].message['content']
    end_time = time.time()
    elapsed_time = format_time(end_time - start_time)
    return result, elapsed_time

def suggest_dataset_purpose(column_names, mod='4o'):
  prompt = f"Given the columns {column_names}, analyze and suggest what this dataset could be about. Give result as a python list."
  response = openai.ChatCompletion.create(
      model=f"gpt-{mod}",
      messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
      max_tokens=1000,
      n=1,
      stop=None,
      temperature=0.7
  )

  return response.choices[0].message['content']

import pandas as pd

def create_and_sort_new_column(df, column1, column2, mod="4o"):
    values1 = df[column1].unique().tolist()
    values2 = df[column2].unique().tolist()

    prompt2 = f"""
          Given two columns, '{column1}' with unique values {values1} and '{column2}' with unique values {values2}, create a new column that
          reflects the semantic relationships between these columns. The new column should not simply combine or replicate the values from both columns.
          There should be minimal overlap between the values of the new column and the original columns. This new column should uniquely and meaningfully
          capture the semantic relationships between '{column1}' and '{column2}', using world knowledge and contextual understanding to create values suitable
          for semantically sorting the dataset. This new column should uniquely
          and meaningfully capture the semantic relationships between {column1} and {column2}, using world knowledge and contextual understanding to create values suitable
          for semantically sorting the dataset.

          Please provide an appropriate name for this new column, the new column values, and an explanation of the criteria for the new column values,
          including the rationale behind the ordering of the values and any world knowledge considered. Additionally, include a mapping from the original
          column values (col1_value, col2_value -> new_col_value) to the new values. Avoid alphabetical sorting and prioritize context and semantic relationships.
          Ensure that the new column values can be used to semantically sort the dataset and that they map to multiple rows.

    """

    response = openai.ChatCompletion.create(
      model=f"gpt-{mod}",
      messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt2}
        ],
      max_tokens=1000,
      n=1,
      stop=None,
      temperature=0.7
  )
    result = response.choices[0].message['content']
    return result

@app.route('/process_dataset', methods=['POST'])
def process_dataset():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        filename = file.filename
        filepath = os.path.join('uploads', filename)
        file.save(filepath)

        df = pd.read_csv(filepath)
        columns = df.columns.tolist()

        action = request.form.get('action')
        constraints = request.form.get('constraints')
        dataset_json = df.to_dict(orient='records')

        if action == "give_sorting_suggestions":
            start_time = time.time()
            sorted_datasets_single, levenshtein_distances_single, sorting_criteria_single, timings_single = sort_dataset_by_semantic_columns(df)
            sorted_datasets_pairs, levenshtein_distances_pairs, sorting_criteria_pairs, timings_pairs = sort_dataset_by_semantic_column_pairs(df)

            combined_sorted_datasets = {**sorted_datasets_single, **sorted_datasets_pairs}
            combined_levenshtein_distances = {**levenshtein_distances_single, **levenshtein_distances_pairs}
            combined_timings = {**timings_single, **timings_pairs}

            end_time = time.time()

            combined_timings[f"Overall time to get the sorted datasets"] = format_time(end_time - start_time)
            return jsonify({
                "sorted_datasets": combined_sorted_datasets,
                "levenshtein_distances": combined_levenshtein_distances,
                "timings": combined_timings,
            })
        elif action == 'suggest_dataset_purpose':
            result = suggest_dataset_purpose(columns).split('\n\n')

            return jsonify({
                "suggestion": result,
                "dataset": dataset_json
            })
        elif action == 'determine_columns':
            # SINGLE COLUMN
            result, elapsed_time = determine_semantic_sortable_columns(df)
            result = result.split('\n\n')

            # MULTIPLE COLUMNS
            # result2 = determine_semantic_sortable_column_pairs(df).split('\n\n')
            return jsonify({
                "suggestions": result,
                "dataset": dataset_json,
                "timing": elapsed_time,
            })
        elif action == 'single_column_sort':
            column_name = request.form.get('column_name', '')
            if column_name and column_name in columns:
                unique_values = df[column_name].unique().tolist()
                # print(constraints)
                if constraints and len(constraints) > 0:
                    result, elapsed_time = semantic_sort_column(column_name, unique_values, constraints)
                else:
                    result, elapsed_time = semantic_sort_column(column_name, unique_values)
                result = result.split('\n\n')
                sort_suggestions = result[-1]
                # match = re.search(r'\[(.*?)\]', sort_suggestions)
                match = re.search(r'\[([^\[\]]*?)\]', sort_suggestions)

                if match:
                    extracted_list_str = match.group(1)
                    extracted_list = [item.strip().strip("'") for item in extracted_list_str.split(',')]
                    print(extracted_list)
                    df[column_name] = pd.Categorical(df[column_name], categories=extracted_list, ordered=True)
                    df = df.sort_values(column_name)
                    dataset_json = df.to_dict(orient='records')
                else:
                    print("No list found.")
                return jsonify({
                    "column_name": column_name,
                    "unique_values": unique_values,
                    "sorting_result": result,
                    "dataset": dataset_json,
                    "timing": elapsed_time,
                })

            else:
                return jsonify({"error": "No column specified or column not found"}), 400

        elif action == 'column_suggestions':
            print(filepath)
            suggestions = get_multiple_columns_suggestions(columns).split('\n\n')
            print(suggestions)
            return jsonify({"suggestions": suggestions, "dataset": dataset_json})
        
        elif action == 'sort_multiple_columns':
            column1 = request.form.get('column1')
            column2 = request.form.get('column2')

            if column1 in columns and column2 in columns:
                values1 = df[column1].tolist()
                values2 = df[column2].tolist()

                if constraints and len(constraints) > 0:
                    result, elapsed_time = semantic_sort_multiple_column(column1, values1, column2, values2, constraints)
                else:
                    result, elapsed_time = semantic_sort_multiple_column(column1, values1, column2, values2)

                result = result.split('\n\n')
                sort_suggestions = result[-1]
                match = re.search(r'\[([^\[\]]*?)\]', sort_suggestions)

                if match:
                    extracted_list_str = match.group(1)
                    extracted_list = [item.strip() for item in extracted_list_str.split(',')]
                    df['combined'] = df[column1] + '-' + df[column2]
                    df['combined'] = pd.Categorical(df['combined'], categories=extracted_list, ordered=True)
                    df = df.sort_values('combined').drop(columns=['combined'])  
                    dataset_json = df.to_dict(orient='records')
                else:
                    print("No list found.")
                return jsonify({
                    "column1": column1,
                    "column2": column2,
                    "sorting_result": result,
                    "dataset": dataset_json
                })
            else:
                return jsonify({"error": "One or both columns not found"}), 400
        elif action == 'generate_new_column':
            column1 = request.form.get('column1')
            column2 = request.form.get('column2')

            if column1 in columns and column2 in columns:
                values1 = df[column1].tolist()
                values2 = df[column2].tolist()
                result = create_and_sort_new_column(df, column1, column2).split('\n\n')
                return jsonify({
                    "column1": column1,
                    "column2": column2,
                    "sorting_result": result,
                    "dataset": dataset_json
                })

            else:
                return jsonify({"error": "One or both columns not found"})
        else:
            return jsonify({"error": "Invalid action specified"}), 400


def identify_joinable_datasets_with_samples(samples, mod):
    prompt = f'''Given the following samples of rows from different datasets, identify which datasets can be joined based on the content of the rows. Explain the join keys and why these datasets can be joined. Provide as many join suggestions as possible with the most probable first.\n\nSamples:\n{samples}
    The last line should contain a list of lists with inner lists having structure [dataset1, dataset2, key1, key2] where dataset1 and dataset2 are the datasets to join and key1 and key2 are their corresponding columns to perform join on. And that last line shouldn't
    contain anything else, nothing before or after the list, just the list.
    
    '''

    response = openai.ChatCompletion.create(
        model=f"gpt-{mod}",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    result = response['choices'][0]['message']['content'].strip()
    return result

def identify_joinable_datasets_with_samples(samples, mod):
    prompt = f'''Given the following samples of rows from different datasets, identify which datasets can be joined based on the content of the rows. Explain the join keys and why these datasets can be joined. Provide as many join suggestions as possible with the most probable first.\n\nSamples:\n{samples}
    The last line should contain a list of lists with inner lists having structure [dataset1, dataset2, key1, key2] where dataset1 and dataset2 are the datasets to join and key1 and key2 are their corresponding columns to perform join on. And that last line shouldn't
    contain anything else, nothing before or after the list, just the list. And, give the dataset names just as they are in samples input, don't modify the names. Also, give the exact column names of the datasets
    '''
    
    response = openai.ChatCompletion.create(
        model=f"gpt-{mod}",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    result = response['choices'][0]['message']['content'].strip()
    return result

# @app.route('/process_multiple_datasets', methods=['POST'])
# def process_multiple_datasets():
#     files = request.files.getlist('files[]')  # Get multiple files
#     if len(files) < 2:
#         return jsonify({"error": "Please upload at least two datasets"}), 400

#     datasets = {}
#     samples = {}

#     # Step 1: Load datasets and extract samples
#     for i, file in enumerate(files):
#         df = pd.read_csv(file)
#         datasets[f'dataset_{i}'] = df
#         samples[f'dataset_{i}'] = df.sample(min(len(df), 5)).to_dict(orient='records')  # Get a sample of each dataset
    
#     samples_str = "\n\n".join([f"{i}: {sample}" for i, sample in samples.items()])
    
#     # Step 2: Identify joinable datasets
#     joinable_suggestion = identify_joinable_datasets_with_samples(samples_str, '4o')
    
#     # Step 3: Extract the join suggestions (list of lists)
#     join_suggestions = re.findall(r'\[([^\[\]]+)\]', joinable_suggestion)
    
#     if not join_suggestions:
#         return jsonify({"error": "No joinable datasets found"}), 400
#     print(join_suggestions)
#     # Step 4: Perform joins on the datasets
#     joined_datasets = {}
#     if len(join_suggestions) > 0:
#         for suggestion in join_suggestions:
#             datasets_to_join = [item.strip().replace("'", "") for item in suggestion.split(',')]
#             if len(datasets_to_join) >= 4:
#                 dataset1_key = datasets_to_join[0].strip()
#                 dataset2_key = datasets_to_join[1].strip()
#                 join_key1 = datasets_to_join[2].strip()
#                 join_key2 = datasets_to_join[3].strip()

#                 df1 = datasets.get(dataset1_key)
#                 df2 = datasets.get(dataset2_key)
                
#                 if df1 is not None and df2 is not None and join_key1 in df1.columns and join_key2 in df2.columns:
#                     joined_df = pd.merge(df1, df2, left_on=join_key1, right_on=join_key2, how='inner')
#                     joined_datasets[f'{dataset1_key}_{dataset2_key}_joined'] = joined_df.to_dict(orient='records')

#     return jsonify({
#         "suggestions": join_suggestions,
#         "joined_datasets": joined_datasets
#     })
@app.route('/process_multiple_datasets', methods=['POST'])
def process_multiple_datasets():
    files = request.files.getlist('files[]')  # Get multiple files
    if len(files) < 2:
        return jsonify({"error": "Please upload at least two datasets"}), 400

    datasets = {}
    samples = {}

    # Step 1: Load datasets and extract samples
    for i, file in enumerate(files):
        fileName = file.filename
        df = pd.read_csv(file)
        datasets[fileName] = df
        samples[fileName] = df.sample(min(len(df), 5)).to_dict(orient='records')  # Get a sample of each dataset
    
    samples_str = "\n\n".join([f"{i}: {sample}" for i, sample in samples.items()])
    
    # Step 2: Identify joinable datasets
    joinable_suggestion = identify_joinable_datasets_with_samples(samples_str, '4o')
    
    # Step 3: Extract the join suggestions (list of lists)
    join_suggestions = re.findall(r'\[([^\[\]]+)\]', joinable_suggestion)
    
    if not join_suggestions:
        return jsonify({"error": "No joinable datasets found"}), 400
    join_suggestions = [item.strip('"') for item in join_suggestions]

    print("join_suggestions", join_suggestions)
    
    # Step 4: Perform joins on the datasets
    joined_datasets = {}

    print(len(join_suggestions))
    if len(join_suggestions) > 0:
        for suggestion in join_suggestions:
            datasets_to_join = [item.strip().replace("'", "") for item in suggestion.split(',')]
            if len(datasets_to_join) >= 4:
                dataset1_key = datasets_to_join[0].strip()
                dataset2_key = datasets_to_join[1].strip()
                join_key1 = datasets_to_join[2].strip()
                join_key2 = datasets_to_join[3].strip()

                df1 = datasets.get(dataset1_key)
                df2 = datasets.get(dataset2_key)
                
                if df1 is not None and df2 is not None and join_key1 in df1.columns and join_key2 in df2.columns:
                    # Perform the join
                    joined_df = pd.merge(df1, df2, left_on=join_key1, right_on=join_key2, how='inner')
                    joined_datasets[f'{dataset1_key}_{dataset2_key}_joined'] = joined_df

    # Step 5: Perform semantic sorting on the joined datasets
    sorted_datasets = {}
    levenshtein_distances = {}
    sorted_datasets_criteria = {}

    for key, joined_df in joined_datasets.items():
        # Convert the DataFrame back to dict for sending as JSON
        sorted_datasets_single, levenshtein_distances_single, sorting_criteria_single, timings = sort_dataset_by_semantic_columns(joined_df)
        sorted_datasets_pairs, levenshtein_distances_pairs, sorting_criteria_pairs, timings = sort_dataset_by_semantic_column_pairs(joined_df)
        
        print("SORTED DATASETS", sorted_datasets_single)
        # Combine sorting results
        combined_sorted_datasets = {**sorted_datasets_single, **sorted_datasets_pairs}
        combined_levenshtein_distances = {**levenshtein_distances_single, **levenshtein_distances_pairs}
        combined_sorting_criterias = {**sorting_criteria_single, **sorting_criteria_pairs}
        
        # Store the sorted datasets
        sorted_datasets[key] = combined_sorted_datasets
        levenshtein_distances[key] = combined_levenshtein_distances
        sorted_datasets_criteria[key] = combined_sorting_criterias
        
    print(levenshtein_distances)
    # Step 6: Return the joined datasets and sorted results
    return jsonify({
        "suggestions": join_suggestions,
        "joined_datasets": {key: df.to_dict(orient='records') for key, df in joined_datasets.items()},
        "sorted_datasets": sorted_datasets,
        "levenshtein_distances": levenshtein_distances,
        "sorted_datasets_criteria": sorted_datasets_criteria
    })


if __name__ == "__main__":
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)