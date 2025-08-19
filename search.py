import os

import shutil

def print_files_with_substring(directory, substring):
    substring = substring.lower()
    for root, dirs, files in os.walk(directory):
        for file in files:
            if substring in file.lower():
                print(os.path.join(root, file))

def copy_files_with_substring(src_directory, dst_directory, substring):
    substring = substring.lower()
    if not os.path.exists(dst_directory):
        os.makedirs(dst_directory)
    for root, dirs, files in os.walk(src_directory):
        for file in files:
            if substring in file.lower():
                src_path = os.path.join(root, file)
                # Preserve subdirectory structure
                rel_path = os.path.relpath(src_path, src_directory)
                dst_path = os.path.join(dst_directory, rel_path)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
                print(f"Copied: {src_path} -> {dst_path}")

# Copy matching files to another directory
copy_files_with_substring('data/data_downloader_whole_content/downloads/City of New York', 'data/datalakes/datagov_datalake/all_tables', 'borough')