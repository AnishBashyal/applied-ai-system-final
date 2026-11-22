"""
The full TasteMatch pipeline:

    request -> validate -> Judge A (keywords) + Judge B (embeddings)
            -> agreement check -> grounded explanation -> answer

Every run is appended to logs/runs.jsonl so what the system did (and why it
refused, when it did) can be read afterwards.
"""

import json
import logging
import os
import time
from typing import Dict, Optional

from src.agreement import decide
from src.explainer import explain, load_notes
from src.gemini_client import GeminiError
from src.judge_a import judge_a
from src.judge_b import build_index, judge_b
from src.recommender import load_songs
from src.validator import validate_query

logger = logging.getLogger("tastematch.pipeline")

RUN_LOG = "logs/runs.jsonl"
TOP_K = 5


def log_run(record: Dict, path: str = RUN_LOG) -> None:
    """Append one run record as a JSON line. Logging problems never stop a run."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError as error:
        logger.error("could not write run log: %s", error)


class Pipeline:
    def __init__(self, songs_path: str = "data/songs.csv", notes_path: str = "data/notes.json",
                 run_log: str = RUN_LOG):
        self.songs = load_songs(songs_path)
        self.songs_by_id = {s["id"]: s for s in self.songs}
        self.notes = load_notes(notes_path)
        self.run_log = run_log
        try:
            self.index = build_index(self.songs)
        except GeminiError as error:
            # no cache and no usable Gemini: Judge B will abstain, Judge A still works
            logger.error("could not build the embedding index: %s", error)
            self.index = None

    def _judge_b(self, query: str) -> Dict:
        if self.index is None:
            return {"judge": "B", "abstained": True, "reason": "embedding index unavailable",
                    "strength": 0.0, "ranking": []}
        return judge_b(query, self.songs, self.index, k=TOP_K)

    def run(self, raw_query) -> Dict:
        """Run one request through the whole pipeline and return the answer."""
        started = time.time()
        check = validate_query(raw_query)

        if not check.ok:
            result = {"status": "rejected", "query": str(raw_query)[:200], "message": check.reason,
                      "confidence": 0.0, "picks": []}
            self._log(result, None, None, None, started)
            return result

        a = judge_a(check.query, self.songs, k=TOP_K)
        b = self._judge_b(check.query)
        decision = decide(a, b, k=TOP_K)

        if decision["decision"] == "refuse":
            result = {"status": "refused", "query": check.query, "message": decision["reason"],
                      "confidence": 0.0, "picks": []}
            self._log(result, a, b, decision, started)
            return result

        explanations = explain(check.query, decision["picks"], self.songs_by_id, self.notes)
        picks = []
        for pick, explanation in zip(decision["picks"], explanations):
            song = self.songs_by_id[pick["id"]]
            picks.append({"title": song["title"], "artist": song["artist"],
                          "explanation": explanation["explanation"], "explained_by": explanation["source"]})

        result = {
            "status": "ok" if decision["decision"] == "recommend" else "warning",
            "query": check.query,
            "message": decision["reason"],
            "warning": decision["warning"],
            "confidence": decision["confidence"],
            "picks": picks,
        }
        self._log(result, a, b, decision, started)
        return result

    def _log(self, result: Dict, a: Optional[Dict], b: Optional[Dict], decision: Optional[Dict],
             started: float) -> None:
        record = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "query": result["query"],
            "status": result["status"],
            "message": result["message"],
            "confidence": result["confidence"],
            "judge_a": None if a is None else {"abstained": a["abstained"], "reason": a["reason"],
                                               "top": [r["title"] for r in a["ranking"]]},
            "judge_b": None if b is None else {"abstained": b["abstained"], "strength": b["strength"],
                                               "top": [r["title"] for r in b["ranking"]]},
            "overlap": None if decision is None else decision["overlap"],
            "picks": [p["title"] for p in result["picks"]],
            "seconds": round(time.time() - started, 2),
        }
        log_run(record, self.run_log)
        logger.info("%s | %s | confidence %.2f", result["status"], result["query"], result["confidence"])
