from src import agreement
from src.agreement import decide


def ranking(judge, ids):
    return {"judge": judge, "abstained": False, "strength": 0.15,
            "ranking": [{"id": i, "title": f"Song {i}", "score": 1.0, "why": f"{judge} likes {i}"} for i in ids]}


def abstained(judge):
    return {"judge": judge, "abstained": True, "reason": "x", "strength": 0.0, "ranking": []}


def test_full_agreement_recommends_with_full_confidence():
    result = decide(ranking("A", [1, 2, 3, 4, 5]), ranking("B", [1, 2, 3, 4, 5]))
    assert result["decision"] == "recommend"
    assert result["confidence"] == 1.0 and result["overlap"] == 1.0
    assert [p["id"] for p in result["picks"]] == [1, 2, 3, 4, 5]


def test_two_shared_picks_is_still_agreement():
    result = decide(ranking("A", [1, 2, 3, 4, 5]), ranking("B", [1, 2, 6, 7, 8]))
    assert result["decision"] == "recommend" and result["confidence"] == 0.4


def test_one_shared_pick_recommends_with_warning():
    result = decide(ranking("A", [1, 2, 3, 4, 5]), ranking("B", [1, 6, 7, 8, 9]))
    assert result["decision"] == "recommend_with_warning"
    assert result["confidence"] == 0.2 and "partly agree" in result["warning"]


def test_no_shared_picks_refuses():
    result = decide(ranking("A", [1, 2, 3, 4, 5]), ranking("B", [6, 7, 8, 9, 10]))
    assert result["decision"] == "refuse" and result["picks"] == []


def test_picks_shared_by_both_judges_come_first():
    result = decide(ranking("A", [1, 2, 3, 4, 5]), ranking("B", [9, 8, 3, 7, 6]))
    assert result["picks"][0]["id"] == 3


def test_picks_carry_each_judges_reason():
    pick = decide(ranking("A", [1, 2, 3, 4, 5]), ranking("B", [1, 2, 3, 4, 5]))["picks"][0]
    assert pick["why_a"] == "A likes 1" and pick["why_b"] == "B likes 1"


def test_when_a_abstains_b_alone_is_allowed_with_a_cap_and_warning():
    result = decide(abstained("A"), ranking("B", [1, 2, 3, 4, 5]))
    assert result["decision"] == "recommend_with_warning"
    assert result["confidence"] <= agreement.SINGLE_JUDGE_CAP
    assert "one judge" in result["warning"]
    assert "why_a" not in result["picks"][0]


def test_when_a_abstains_b_must_be_clearly_strong():
    weak = ranking("B", [1, 2, 3, 4, 5])
    weak["strength"] = 0.09  # above the floor, below the stand-alone bar
    assert decide(abstained("A"), weak)["decision"] == "refuse"


def test_weak_b_does_not_count_when_a_has_an_opinion():
    weak = ranking("B", [1, 2, 3, 4, 5])
    weak["strength"] = 0.03
    result = decide(ranking("A", [1, 2, 3, 4, 5]), weak)
    assert result["decision"] == "recommend_with_warning"
    assert result["confidence"] == agreement.A_ALONE_CONFIDENCE
    assert "no clear match" in result["reason"]


def test_a_alone_when_gemini_is_unavailable():
    result = decide(ranking("A", [1, 2, 3, 4, 5]), abstained("B"))
    assert result["decision"] == "recommend_with_warning"
    assert "unavailable" in result["reason"]


def test_both_abstaining_refuses():
    result = decide(abstained("A"), abstained("B"))
    assert result["decision"] == "refuse" and result["confidence"] == 0.0


def test_nonsense_with_weak_b_and_no_keywords_refuses():
    weak = ranking("B", [1, 2, 3, 4, 5])
    weak["strength"] = 0.04
    assert decide(abstained("A"), weak)["decision"] == "refuse"
