"""
Calibrates Judge B's confidence floor.

Runs a set of real music requests and a set of nonsense or off-topic requests
through Judge B's embeddings and prints, for each one, the top similarity and
the "strength": how far the top similarity sits above the catalog average.
Needs GEMINI_API_KEY. Run with:  python -m eval.calibrate_threshold
"""

import numpy as np

from src import gemini_client
from src.judge_b import build_index
from src.recommender import load_songs

REAL = [
    "cozy rainy afternoon", "mellow music for studying late at night", "gym workout",
    "happy summer pop", "sad heartbreak songs", "romantic dinner jazz",
    "loud aggressive metal", "calm acoustic folk", "music for a road trip",
    "dreamy hazy evening", "angry rebellious punk", "relaxing sleep music",
]
NONSENSE = [
    "asdf qwerty", "zzzz xxxx", "blah blah blah", "the quick brown fox",
    "how do I bake bread", "what is the capital of France", "my cat is hungry",
    "tax return deadline", "qwertyuiop",
]


def measure(query, index):
    vector = np.array(gemini_client.embed_texts([query])[0])
    vector = vector / np.linalg.norm(vector)
    sims = np.sort(index @ vector)[::-1]
    return sims[0], sims[0] - sims.mean()


def main():
    index = build_index(load_songs("data/songs.csv"))
    print(f"{'query':42s} top_sim  strength")
    for label, queries in (("REAL", REAL), ("NONSENSE / OFF-TOPIC", NONSENSE)):
        print(f"-- {label}")
        results = [measure(q, index) for q in queries]
        for query, (top, strength) in zip(queries, results):
            print(f"{query:42s} {top:.3f}    {strength:.3f}")
        strengths = [s for _, s in results]
        print(f"   strength min {min(strengths):.3f}  max {max(strengths):.3f}")


if __name__ == "__main__":
    main()
