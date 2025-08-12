from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from algorithms.prompts import compute_semantic_utility_prompt
from algorithms.llm_utils import call_gpt
from algorithms.embedding_utils import embed_text
from tqdm import tqdm

def compute_column_uniqueness(input_columns: list[str], candidate_columns: list[str]) -> float:
    input_embeddings = [embed_text(col) for col in input_columns if embed_text(col) is not None]
    candidate_embeddings = [embed_text(col) for col in candidate_columns if embed_text(col) is not None]

    if not input_embeddings or not candidate_embeddings:
        return 0.0
    
    similarities = []
    for cand_emb in candidate_embeddings:
        top_sim = max(cosine_similarity([cand_emb], input_embeddings)[0])
        uniqueness = 1 - top_sim
        similarities.append(uniqueness)

    return np.mean(similarities)


def compute_semantic_utility(input_columns: list[str], candidate_columns: list[str]) -> float:
    prompt = compute_semantic_utility_prompt(input_columns, candidate_columns)
    response = call_gpt(prompt)

    try:
        return float(response.strip())  
    except:
        print("\u26a0\ufe0f Could not parse semantic utility score:", response)
        exit(0)
        return 0.0
    

def compute_semantic_interestingness(input_columns: list[str], candidate_colums: list[str]) -> float:
    semantic_utility = compute_semantic_utility(input_columns, candidate_colums)
    uniqueness = compute_column_uniqueness(input_columns, candidate_colums)
    return (semantic_utility + uniqueness) / 2


def update_suggestions_with_semantic_scores(df, input_columns):
    scores = []
    for _, row in tqdm(list(df.iterrows())):
        candidate_column = row["Sort Attribute"]
        candidate_columns = [col.strip() for col in str(row["Required Column"]).split(",")]
        score = compute_semantic_interestingness(input_columns, candidate_columns)
        scores.append(score)
    df["Interestingness"] = scores
    return df