"""
Agreement check: turns Judge A's and Judge B's opinions into one decision.

The judges work independently (A on keywords, B on description meaning), so when
their top picks overlap that is real evidence the picks are good. When they
disagree, or only one has an opinion, the confidence drops and the answer
carries a warning. When neither can be trusted, the system refuses.

Thresholds come from eval/calibrate_threshold.py: across 12 real requests B's
strength was at least 0.076, across 9 nonsense requests at most 0.070.
"""

from typing import Dict, List

B_MIN_STRENGTH = 0.075        # below this, B does not count as having an opinion
B_ALONE_MIN_STRENGTH = 0.10   # when A abstains, B must be clearly above the floor
AGREE_OVERLAP = 0.4           # at least 2 of 5 shared picks counts as agreement
A_ALONE_CONFIDENCE = 0.4      # keywords matched but nothing semantic confirmed them
SINGLE_JUDGE_CAP = 0.5        # one judge alone never earns more than this


def _ids(judge: Dict) -> List[int]:
    return [item["id"] for item in judge["ranking"]]


def _merge(a: Dict, b: Dict, k: int) -> List[Dict]:
    """Combine both rankings (rank points from each judge) and keep the top k."""
    by_id = {}
    for judge in (a, b):
        for position, item in enumerate(judge["ranking"]):
            entry = by_id.setdefault(item["id"], {"id": item["id"], "title": item["title"], "points": 0})
            entry["points"] += len(judge["ranking"]) - position
            entry[f"why_{judge['judge'].lower()}"] = item["why"]
    return sorted(by_id.values(), key=lambda e: -e["points"])[:k]


def _single(judge: Dict, k: int) -> List[Dict]:
    name = judge["judge"].lower()
    return [
        {"id": item["id"], "title": item["title"], f"why_{name}": item["why"]}
        for item in judge["ranking"][:k]
    ]


def decide(a: Dict, b: Dict, k: int = 5) -> Dict:
    """Combine the two judges' opinions into one decision.

    Returns decision ("recommend", "recommend_with_warning" or "refuse"),
    confidence (0 to 1), picks, overlap, reason and warning.
    """
    a_ok = not a["abstained"]
    b_ok = (not b["abstained"]) and b["strength"] >= B_MIN_STRENGTH

    def result(decision, confidence, picks, reason, overlap=None, warning=""):
        return {"decision": decision, "confidence": round(confidence, 2), "picks": picks,
                "overlap": overlap, "reason": reason, "warning": warning}

    if a_ok and b_ok:
        shared = set(_ids(a)[:k]) & set(_ids(b)[:k])
        overlap = len(shared) / k
        picks = _merge(a, b, k)
        if overlap >= AGREE_OVERLAP:
            return result("recommend", overlap, picks,
                          f"both judges agree on {len(shared)} of {k} picks", overlap)
        if overlap > 0:
            return result("recommend_with_warning", overlap, picks,
                          f"judges share only {len(shared)} of {k} picks", overlap,
                          "the two judges only partly agree, so treat these picks with care")
        return result("refuse", 0.0, [], "the two judges picked completely different songs", 0.0)

    if a_ok:
        why = "the meaning-based judge is unavailable" if b["abstained"] else \
              "the meaning-based judge found no clear match"
        return result("recommend_with_warning", A_ALONE_CONFIDENCE, _single(a, k),
                      f"only the keyword judge had an opinion ({why})",
                      warning="only one judge had an opinion, so this is less certain")

    if b_ok and b["strength"] >= B_ALONE_MIN_STRENGTH:
        confidence = min(SINGLE_JUDGE_CAP, b["strength"] * 3)
        return result("recommend_with_warning", confidence, _single(b, k),
                      "only the meaning-based judge had an opinion (no keywords recognised)",
                      warning="only one judge had an opinion, so this is less certain")

    return result("refuse", 0.0, [], "no confident match: the request could not be understood")
