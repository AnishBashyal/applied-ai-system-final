"""
Judge B: the meaning-based judge.

Embeds the song descriptions and the user's request with Gemini and ranks songs
by cosine similarity. It never looks at the genre/mood labels or at Judge A, so
the two judges can only agree by reaching the same answer separately.

Song embeddings are cached on disk (keyed by a hash of the text, model and
size), so only the request needs a Gemini call on a normal run.
"""

import hashlib
import json
import logging
import os
from typing import Dict, List

import numpy as np

from src import gemini_client
from src.gemini_client import GeminiError

logger = logging.getLogger("tastematch.judge_b")

CACHE_PATH = "data/embeddings_cache.json"


def _cache_key(text: str) -> str:
    raw = f"{gemini_client.EMBED_MODEL}|{gemini_client.EMBED_DIMENSIONS}|{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_cache(path: str) -> Dict[str, List[float]]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        logger.warning("could not read embedding cache at %s, rebuilding", path)
        return {}


def build_index(songs: List[Dict], cache_path: str = CACHE_PATH) -> np.ndarray:
    """Return a (songs x dimensions) array of unit-length description vectors.

    Descriptions missing from the cache are embedded and the cache is updated.
    """
    cache = _load_cache(cache_path)
    missing = [s["description"] for s in songs if _cache_key(s["description"]) not in cache]
    if missing:
        logger.info("embedding %d song descriptions", len(missing))
        for text, vector in zip(missing, gemini_client.embed_texts(missing)):
            cache[_cache_key(text)] = vector
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f)

    matrix = np.array([cache[_cache_key(s["description"])] for s in songs], dtype=float)
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def judge_b(query: str, songs: List[Dict], index: np.ndarray, k: int = 5) -> Dict:
    """Return Judge B's opinion on a query, in the same shape as Judge A's.

    ranking holds the top k songs with their cosine similarity as the score.
    strength is how far the best similarity sits above the catalog average: real
    requests stand out from the pack, nonsense does not (see eval/calibrate_threshold.py).
    If Gemini cannot be reached, Judge B abstains instead of raising.
    """
    try:
        vector = np.array(gemini_client.embed_texts([query])[0], dtype=float)
    except GeminiError as error:
        logger.error("judge B abstaining: %s", error)
        return {"judge": "B", "abstained": True, "reason": f"embedding failed: {error}",
                "strength": 0.0, "ranking": []}

    vector = vector / np.linalg.norm(vector)
    similarities = index @ vector
    order = np.argsort(-similarities)[:k]

    ranking = [
        {
            "id": songs[i]["id"],
            "title": songs[i]["title"],
            "score": round(float(similarities[i]), 3),
            "why": f'description "{songs[i]["description"]}" (similarity {similarities[i]:.2f})',
        }
        for i in order
    ]
    strength = float(similarities[order[0]] - similarities.mean())
    return {"judge": "B", "abstained": False, "reason": "ranked by description similarity",
            "strength": round(strength, 3), "ranking": ranking}
