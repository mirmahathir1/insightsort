import os
import json
import hashlib
from pathlib import Path
import openai                         # make sure openai‑python is installed

openai.api_key = 'sk-proj-zvfr2IvWfqEUqsnmwIBJT3BlbkFJMxh6YiSgfcG6vEcMGJ35'  # ← ideally load from env

CACHE_DIR = Path("llmcache")
CACHE_DIR.mkdir(exist_ok=True)        # create if it doesn’t exist


def _cache_path(prompt: str) -> Path:
    """
    Deterministically map a prompt to a cache‑file path.
    Using SHA‑256 avoids problems with very long or filesystem‑unsafe filenames.
    """
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def call_gpt(prompt: str, model: str = "gpt-4o", temperature: float = 0.4) -> str:
    """
    Return GPT response, using a disk cache keyed by the full prompt text.
    """
    cache_file = _cache_path(prompt)

    # ─── 1) Return cached value if present ──────────────────────────────────────
    if cache_file.exists():
        with cache_file.open("r", encoding="utf-8") as f:
            cached_content = json.load(f)["content"]
        # print("from cache:", cached_content)
        return cached_content

    # ─── 2) Otherwise query the API ─────────────────────────────────────────────
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        content = response["choices"][0]["message"]["content"]
        # print("from API:", content)

        # ─── 3) Persist to cache ───────────────────────────────────────────────
        with cache_file.open("w", encoding="utf-8") as f:
            json.dump({"content": content}, f, ensure_ascii=False, indent=2)

        return content

    except Exception as e:
        print("GPT Error:", e)
        return None



def parse_suggestion(gpt_output):
    try:
        return json.loads(gpt_output)
    except json.JSONDecodeError:
        print("Failed to parse GPT output.")
        return {}





