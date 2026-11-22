"""
Command line runner for TasteMatch.

  python -m src.main                       original demo: top 5 for each test profile
  python -m src.main --query "your text"   ask for music in plain words
"""

import argparse
import logging

from tabulate import tabulate

from src.recommender import load_songs, recommend_songs

# normal profiles
PROFILES = {
    "High-Energy Pop": {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False},
    "Chill Lofi": {"genre": "lofi", "mood": "chill", "energy": 0.35, "likes_acoustic": True},
    "Deep Intense Rock": {"genre": "rock", "mood": "intense", "energy": 0.92, "likes_acoustic": False},
    # adversarial profiles, made to see if the scoring gets tricked
    "Sad but Energetic": {"genre": "pop", "mood": "sad", "energy": 0.9, "likes_acoustic": False},
    "Unknown Genre (k-pop)": {"genre": "k-pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False},
    "Conflicting Taste": {"genre": "classical", "mood": "aggressive", "energy": 0.95, "likes_acoustic": True},
}


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    for name, user_prefs in PROFILES.items():
        recommendations = recommend_songs(user_prefs, songs, k=5)

        print(f"\n=== {name} ===")
        print(f"User profile: {user_prefs}")
        print("\nTop recommendations:\n")
        # one row per song, with each reason on its own line in the last column
        rows = [
            [i, song["title"], song["artist"], score, explanation.replace("; ", "\n")]
            for i, (song, score, explanation) in enumerate(recommendations, start=1)
        ]
        print(tabulate(rows, headers=["#", "Song", "Artist", "Score", "Why"], tablefmt="grid", floatfmt=".2f"))
        print()


def run_query(query: str) -> None:
    """Send a free-text request through the full pipeline and print the answer."""
    from src.pipeline import Pipeline

    result = Pipeline().run(query)
    print(f"Request:    {result['query']}")
    print(f"Status:     {result['status'].upper()}   (confidence {result['confidence']:.2f})")
    print(f"Decision:   {result['message']}")
    if result.get("warning"):
        print(f"Warning:    {result['warning']}")
    for i, pick in enumerate(result["picks"], start=1):
        print(f"\n{i}. {pick['title']} - {pick['artist']}")
        print(f"   {pick['explanation']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TasteMatch music recommender")
    parser.add_argument("--query", help="ask for music in plain words, e.g. 'calm music for studying'")
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    if args.query is not None:
        run_query(args.query)
    else:
        main()
