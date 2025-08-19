import codecs
import os
import re
import pandas as pd

def remove_non_utf8_lines(filename):
    with codecs.open(filename, 'r', encoding='utf-8', errors='ignore') as f_in:
        lines = f_in.readlines()

    with codecs.open(filename, 'w', encoding='utf-8') as f_out:
        for line in lines:
            try:
                line.encode('utf-8')
                f_out.write(line)
            except UnicodeEncodeError:
                continue


def sanitize_csv_files(folder_path):
    """
    Reads all CSV files in the folder, renames files by removing whitespace and replacing non-alphanumeric characters with '_',
    and sanitizes column names similarly. Uses remove_non_utf8_lines before reading CSVs.
    """
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.csv'):
            base, ext = os.path.splitext(filename)
            # Remove leading/trailing whitespace and replace non-alphanumeric with '_', but keep .csv extension
            sanitized_base = re.sub(r'\W+', '_', base.strip())
            sanitized_base = re.sub(r'_+', '_', sanitized_base)  # Collapse multiple underscores
            sanitized_base = re.sub(r'^_+|_+$', '', sanitized_base)  # Remove leading/trailing underscores
            sanitized_name = sanitized_base + ext  # ext is '.csv'
            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, sanitized_name)
            if old_path != new_path:
                os.rename(old_path, new_path)
            # Remove non-UTF8 lines before reading
            remove_non_utf8_lines(new_path)
            # Read CSV and sanitize column names
            df = pd.read_csv(new_path)
            df.columns = [re.sub(r'^_+|_+$', '', re.sub(r'_+', '_', re.sub(r'\W+', '_', col.strip()))) for col in df.columns]
            df.to_csv(new_path, index=False)

if __name__ == "__main__":
    sanitize_csv_files('data/datalakes/datagov_datalake/all_tables')

