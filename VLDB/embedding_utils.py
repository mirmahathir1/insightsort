from sentence_transformers import SentenceTransformer
import numpy as np 


_model = SentenceTransformer("all-MiniLM-l6-v2")

def embed_text(text: str) -> np.ndarray:
    '''Embed a single string'''
    return _model.encode(text, convert_to_numpy=True)


def embed_column_values(values: list[str]) -> np.ndarray:
    '''Embed a column by concatenating sample values'''
    if not values:
        return None

    sample = ", ".join(map(str, values[:10])) # use top 10 values
    return embed_text(sample)


def embed_column_semantic_type(name: str, sample_values: list[str]) -> np.ndarray:
    '''Create a semantic type embedding based on name + values'''
    values_str = ", ".join(map(str, sample_values[:10]))  # Safely cast values to strings
    text = f"{name}: {values_str}"
    return embed_text(text)