import pandas as pd
import os

# Hardcoded path to the input CSV file
input_csv_path = 'results/datalakes/mitdwh_datalake/input_tables/Employee_directory.csv'  # TODO: Replace with your actual path

# List of columns to keep (placeholders)
columns_to_keep = ['Full Name', 'Primary Title', 'Department Name']  # TODO: Replace with your actual column names

# Read the CSV file
df = pd.read_csv(input_csv_path)

# Filter the DataFrame to keep only the selected columns
df_reduced = df[columns_to_keep]

# Create the output path by appending '_reduced' before the file extension
base, ext = os.path.splitext(input_csv_path)
output_csv_path = f"{base}_reduced{ext}"

# Save the reduced DataFrame to the new CSV file
df_reduced.to_csv(output_csv_path, index=False)
