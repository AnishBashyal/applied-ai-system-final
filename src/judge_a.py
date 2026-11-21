"""
Judge A: the rule-based judge.

Parses the request with the keyword parser, then ranks songs with the original
scorer. It has no LLM in it, so it can never share a mistake with Judge B.

If the parser finds neither a genre nor a mood, Judge A abstains: the scorer
would only be comparing energy to a default, which says nothing about the request.
"""

from typing import Dict, List

from src.recommender import recommend_songs
from src.text_parser import parse_query


def judge_a(query: str, songs: List[Dict], k: int = 5) -> Dict:
    """Return Judge A's opinion on a query.

    The result always has: judge, abstained, reason, prefs, ranking.
    ranking is empty when the judge abstains.
    """
    prefs = parse_query(query)

    if prefs["genre"] is None and prefs["mood"] is None:
        return {
            "judge": "A",
            "abstained": True,
            "reason": "no genre or mood recognised in the request",
            "prefs": prefs,
            "ranking": [],
        }

    ranking = [
        {"id": song["id"], "title": song["title"], "score": round(score, 2), "why": why}
        for song, score, why in recommend_songs(prefs, songs, k=k)
    ]
    return {
        "judge": "A",
        "abstained": False,
        "reason": "matched: " + ", ".join(prefs["matched"]),
        "prefs": prefs,
        "ranking": ranking,
    }
