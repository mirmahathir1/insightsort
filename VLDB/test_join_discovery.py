import pandas as pd
from index_builder import build_indexes_from_datalake
from join_discovery import load_indexes, find_joinable_columns, find_semantic_matches

datalake = {
    "health_indicators": pd.DataFrame({
        "country": ["India", "USA", "UK"],
        "life_expectancy": [70, 78, 81]
    }),
    "economic_data": pd.DataFrame({
        "country_name": ["India", "USA", "UK"],
        "gdp": [2.8, 21.4, 2.6]
    }),
    "climate": pd.DataFrame({
        "nation": ["India", "USA", "UK"],
        "avg_temperature": [24, 12, 10]
    })
}

build_indexes_from_datalake(datalake, save_dir="test_indexes")

# Load the built indexes
join_index, semantic_index = load_indexes("test_indexes")

# Simulate an input table column (e.g., from uploaded countries table)
input_col_values = ["India", "USA", "UK"]

# Test join discovery
join_matches = find_joinable_columns(input_col_values, join_index)
print("\n🔗 Joinable columns:")
for (table, col), dist in join_matches:
    print(f"{table}.{col} → distance: {dist:.4f}")

# Test semantic matching for an LLM attribute like "life expectancy"
semantic_matches = find_semantic_matches("life expectancy", semantic_index)
print("\n🧠 Semantic matches for 'life expectancy':")
for (table, col), dist in semantic_matches:
    print(f"{table}.{col} → distance: {dist:.4f}")
