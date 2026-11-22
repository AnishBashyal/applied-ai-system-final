"""
Grounded explainer: the generation step of the RAG pipeline.

Gemini writes a short "why this song" for each pick, using only the retrieved
material: the song's description and the notes for its genre and mood. It must
return an exact quote from that material with every explanation. Plain code then
checks the quote really appears there. If it does not (or Gemini is down), that
song falls back to its plain retrieved description.
"""

import json
import logging
from typing import Dict, List

from src import gemini_client
from src.gemini_client import GeminiError

logger = logging.getLogger("tastematch.explainer")

SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "explanation": {"type": "string"},
            "quote": {"type": "string"},
        },
        "required": ["title", "explanation", "quote"],
    },
}


def load_notes(path: str = "data/notes.json") -> Dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _material(song: Dict, notes: Dict) -> str:
    """Everything the explainer is allowed to use for one song."""
    parts = [song["description"]]
    for kind, label in (("genres", "genre"), ("moods", "mood")):
        text = notes[kind].get(song[label])
        if text:
            parts.append(text)
    return " ".join(parts)


def _prompt(query: str, picks: List[Dict], materials: Dict[str, str]) -> str:
    blocks = "\n".join(f'- {title}: {text}' for title, text in materials.items())
    titles = ", ".join(p["title"] for p in picks)
    return (
        f'A user asked for music: "{query}"\n\n'
        f"Retrieved material about each recommended song:\n{blocks}\n\n"
        f"For each of these songs: {titles}\n"
        "write one short explanation (under 25 words) of why it fits the request. "
        "Use only the retrieved material above. For each song also give a short exact "
        "quote copied word for word from that song's material that supports the explanation."
    )


def _grounded(item: Dict, material: str) -> bool:
    quote = item.get("quote", "").strip().lower()
    return len(quote) >= 8 and quote in material.lower()


def explain(query: str, picks: List[Dict], songs_by_id: Dict[int, Dict], notes: Dict) -> List[Dict]:
    """Return one explanation per pick: {title, explanation, source}.

    source is "gemini" when the explanation passed the grounding check and
    "retrieved" when the plain retrieved description was used instead.
    """
    materials = {p["title"]: _material(songs_by_id[p["id"]], notes) for p in picks}

    written = {}
    try:
        reply = json.loads(gemini_client.generate_text(_prompt(query, picks, materials), json_schema=SCHEMA))
        written = {item["title"]: item for item in reply if isinstance(item, dict) and "title" in item}
    except (GeminiError, json.JSONDecodeError, TypeError) as error:
        logger.warning("explainer falling back to retrieved text: %s", error)

    results = []
    for pick in picks:
        title = pick["title"]
        item = written.get(title)
        if item and _grounded(item, materials[title]):
            results.append({"title": title, "explanation": item["explanation"].strip(), "source": "gemini"})
        else:
            if item:
                logger.warning("explanation for %s failed the grounding check", title)
            results.append({"title": title, "explanation": songs_by_id[pick["id"]]["description"],
                            "source": "retrieved"})
    return results
