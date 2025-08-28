import os
import json
import hashlib
from pathlib import Path
import openai                         # make sure openai‑python is installed
import re
from data_path import data_path

# model_name = "gpt-4o"
model_name = "gpt-5"


# openai.api_key = 'sk-proj-zvfr2IvWfqEUqsnmwIBJT3BlbkFJMxh6YiSgfcG6vEcMGJ35'  # ← ideally load from env
openai.api_key = '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'

def _cache_path(prompt: str, model) -> Path:
    """
    Deterministically map a prompt to a cache‑file path.
    Using SHA‑256 avoids problems with very long or filesystem‑unsafe filenames.
    """
    CACHE_DIR = data_path() / Path(f"llmcache_{model}")
    CACHE_DIR.mkdir(exist_ok=True)        # create if it doesn’t exist
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def call_gpt(prompt: str, temperature: float = 1) -> str:
    """
    Return GPT response, using a disk cache keyed by the full prompt text.
    """
    cache_file = _cache_path(prompt, model=model_name)

    # ─── 1) Return cached value if present ──────────────────────────────────────
    if cache_file.exists():
        with cache_file.open("r", encoding="utf-8") as f:
            cached_content = json.load(f)["content"]
        # print("from cache:", cached_content)
        return cached_content

    # ─── 2) Otherwise query the API ─────────────────────────────────────────────
    response = openai.ChatCompletion.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    content = response["choices"][0]["message"]["content"]
    # print("from API:", content)

    # ─── 3) Persist to cache ───────────────────────────────────────────────
    with cache_file.open("w", encoding="utf-8") as f:
        json.dump({"content": content}, f, ensure_ascii=False, indent=2)

    return content


def parse_suggestion(gpt_output):
    return json.loads(gpt_output)

def extract_json_object(text: str):
    """
    Extracts the first valid JSON object or array from a string and returns it as a Python object.
    Raises ValueError if no valid JSON is found.
    """
    # Regex to match JSON objects or arrays
    json_pattern = re.compile(r'(\{.*\}|\[.*\])', re.DOTALL)

    matches = json_pattern.findall(text)
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue  # Try the next match if parsing fails

    return {}
    raise ValueError("No valid JSON object found in the input string.")




