from sentence_transformers import SentenceTransformer
import numpy as np 
from numpy.linalg import norm


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

def _cosine_distance(a: np.ndarray, b: np.ndarray, eps: float = 1e-9) -> float:
    """
    Normalized cosine distance in the range [0, 1].

    - 0 → vectors are identical (cos θ = 1)
    - 1 → vectors point in exactly opposite directions (cos θ = –1)

    Parameters
    ----------
    a, b : np.ndarray
        1-D vectors of equal length.
    eps : float, optional
        Small constant to avoid division by zero when a or b is the zero vector.

    Returns
    -------
    float
        The normalized cosine distance between *a* and *b*.
    """
    sim = np.dot(a, b) / (norm(a) * norm(b) + eps)   # cosine similarity ∈ [–1, 1]
    dist = 0.5 * (1.0 - sim)                         # rescale to [0, 1]
    return float(np.clip(dist, 0.0, 1.0))