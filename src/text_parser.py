"""
Judge A's query parser: turns free text into the prefs dict that score_song uses.

It is purely rule-based (keyword lookup, no LLM), so Judge A never depends on
Gemini. Anything it cannot recognise is left out, and the result says so.
"""

import re
from collections import Counter
from typing import Dict, List, Tuple

from src.lexicon import ACOUSTIC_WORDS, ENERGY_WORDS, GENRE_WORDS, MOOD_WORDS

DEFAULT_ENERGY = 0.5

# a term right after one of these words (or one word later) is ignored: "not sad"
NEGATION = re.compile(r"\b(?:not|no|without|never|non)\s+(?:\w+\s+)?$")


def _find_terms(text: str, table: Dict) -> List[Tuple[int, str]]:
    """Return (position, term) for every table word found in text.

    Longer phrases are matched first and blanked out, so "indie pop" is not
    also counted as "pop".
    """
    found = []
    working = text
    for term in sorted(table, key=len, reverse=True):
        pattern = r"(?<![\w-])" + re.escape(term) + r"(?![\w-])"
        for match in re.finditer(pattern, working):
            # drop negated terms ("not sad"), but still blank them so shorter words don't re-match
            if not NEGATION.search(working[:match.start()]):
                found.append((match.start(), term))
            working = working[:match.start()] + " " * len(term) + working[match.end():]
    return sorted(found)


def parse_query(text: str) -> Dict:
    """Parse free text into prefs for the original scorer.

    Returns a dict with the usual prefs keys (genre, mood, energy and, only if
    the text mentions it, likes_acoustic) plus "matched": the words that were
    recognised and "recognised": whether anything useful was found at all.
    """
    text = text.lower()

    genres = _find_terms(text, GENRE_WORDS)
    moods = _find_terms(text, MOOD_WORDS)
    energies = _find_terms(text, ENERGY_WORDS)
    acoustics = _find_terms(text, ACOUSTIC_WORDS)

    prefs = {
        # first genre mentioned wins; None never equals a real genre
        "genre": GENRE_WORDS[genres[0][1]] if genres else None,
        "energy": DEFAULT_ENERGY,
        "mood": None,
    }

    if moods:
        counts = Counter(MOOD_WORDS[term] for _, term in moods)
        best = max(counts.values())
        # on a tie, the mood mentioned first in the text wins
        for _, term in moods:
            if counts[MOOD_WORDS[term]] == best:
                prefs["mood"] = MOOD_WORDS[term]
                break

    if energies:
        prefs["energy"] = round(sum(ENERGY_WORDS[t] for _, t in energies) / len(energies), 2)

    if acoustics:
        prefs["likes_acoustic"] = ACOUSTIC_WORDS[acoustics[0][1]]

    # each recognised word once, in the order it appeared
    ordered = [term for _, term in sorted(genres + moods + energies + acoustics)]
    prefs["matched"] = list(dict.fromkeys(ordered))
    prefs["recognised"] = bool(genres or moods or energies or acoustics)
    return prefs
