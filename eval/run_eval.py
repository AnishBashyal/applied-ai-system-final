"""
Evaluation harness: runs fixed requests through the whole pipeline and checks
each result against what we expect.

Needs GEMINI_API_KEY for the full result. Run with:  python -m eval.run_eval

Each case states the status the system should return. Cases that should be
answered also name genres, and at least one recommended song must be in them,
so a confident answer full of wrong songs does not pass. A final check runs a
few requests twice and compares the recommended songs.
"""

import os
import sys

from tabulate import tabulate

from src.pipeline import Pipeline
from src.recommender import load_songs

EVIDENCE_DIR = "logs/evidence"
RUN_LOG = f"{EVIDENCE_DIR}/eval_runs.jsonl"

# (request, allowed statuses, genres at least one pick must be in, what it tests)
CASES = [
    ("mellow music for studying late at night", {"ok"}, {"lofi", "ambient"}, "keywords and meaning agree"),
    ("gym workout rock", {"ok"}, {"rock", "edm", "pop", "punk", "metal"}, "high-energy request"),
    ("romantic dinner jazz", {"ok"}, {"jazz", "r&b", "soul"}, "genre and mood together"),
    ("happy summer pop", {"ok"}, {"pop", "indie pop", "reggae", "edm"}, "upbeat request"),
    ("calm acoustic folk", {"ok"}, {"folk", "classical", "ambient"}, "acoustic preference"),
    ("angry rebellious punk", {"ok"}, {"punk", "metal", "rock"}, "aggressive request"),
    ("cozy rainy afternoon", {"warning"}, {"lofi", "jazz", "ambient", "indie pop"},
     "no keywords: Judge A abstains, B answers alone"),
    ("asdf qwerty", {"refused"}, None, "letters but meaningless"),
    ("how do I bake bread", {"refused"}, None, "off-topic request"),
    ("tax return deadline", {"refused"}, None, "off-topic request"),
    ("", {"rejected"}, None, "empty input"),
    ("12345 !!! ???", {"rejected"}, None, "no letters"),
    ("music " * 60, {"rejected"}, None, "over the length limit"),
]

CONSISTENCY_QUERIES = ["mellow music for studying late at night", "gym workout rock", "cozy rainy afternoon"]


def evaluate(pipeline, genre_of):
    rows, passed, answered_conf = [], 0, []
    for query, allowed, genres, tests in CASES:
        result = pipeline.run(query)
        ok = result["status"] in allowed
        detail = ""
        if ok and genres is not None:
            pick_genres = {genre_of[p["title"]] for p in result["picks"]}
            ok = bool(pick_genres & genres)
            detail = ", ".join(p["title"] for p in result["picks"][:2])
        if result["picks"]:
            answered_conf.append(result["confidence"])
        passed += ok
        shown = (query if len(query) <= 38 else query[:35] + "...") or "(empty)"
        rows.append([shown, tests, "/".join(sorted(allowed)), result["status"],
                     f"{result['confidence']:.2f}", detail, "PASS" if ok else "FAIL"])
    return rows, passed, answered_conf


def consistency(pipeline):
    rows, passed = [], 0
    for query in CONSISTENCY_QUERIES:
        first = [p["title"] for p in pipeline.run(query)["picks"]]
        second = [p["title"] for p in pipeline.run(query)["picks"]]
        same = first == second and bool(first)
        passed += same
        rows.append([query, "same 5 songs both runs" if same else "picks differed", "PASS" if same else "FAIL"])
    return rows, passed


def main() -> int:
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    open(RUN_LOG, "w").close()  # start each evaluation with a clean run log

    pipeline = Pipeline(run_log=RUN_LOG)
    genre_of = {s["title"]: s["genre"] for s in load_songs("data/songs.csv")}

    rows, passed, confidences = evaluate(pipeline, genre_of)
    print("OUTCOME CHECKS")
    print(tabulate(rows, headers=["Request", "What it tests", "Expected", "Got", "Conf", "Top picks", "Result"],
                   tablefmt="github"))

    c_rows, c_passed = consistency(pipeline)
    print("\nCONSISTENCY CHECKS (each request run twice)")
    print(tabulate(c_rows, headers=["Request", "Outcome", "Result"], tablefmt="github"))

    total = len(rows) + len(c_rows)
    print(f"\nSUMMARY: {passed + c_passed}/{total} checks passed "
          f"({passed}/{len(rows)} outcome, {c_passed}/{len(c_rows)} consistency)")
    if confidences:
        print(f"Average confidence on answered requests: {sum(confidences) / len(confidences):.2f}")
    return 0 if passed + c_passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
