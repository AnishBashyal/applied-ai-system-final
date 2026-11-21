from src.judge_a import judge_a
from src.recommender import load_songs

SONGS = load_songs("data/songs.csv")


def test_normal_query_returns_a_ranking():
    result = judge_a("chill lofi for studying", SONGS)
    assert result["abstained"] is False
    assert len(result["ranking"]) == 5
    assert result["ranking"][0]["title"] in ("Library Rain", "Midnight Coding", "Focus Flow")


def test_ranking_is_sorted_best_first():
    scores = [r["score"] for r in judge_a("rock workout", SONGS)["ranking"]]
    assert scores == sorted(scores, reverse=True)


def test_each_pick_comes_with_a_reason():
    assert all(r["why"] for r in judge_a("happy pop", SONGS)["ranking"])


def test_vibe_query_makes_judge_a_abstain():
    result = judge_a("cozy rainy afternoon", SONGS)
    assert result["abstained"] is True
    assert result["ranking"] == []
    assert "no genre or mood" in result["reason"]


def test_gibberish_makes_judge_a_abstain():
    assert judge_a("asdf qwerty", SONGS)["abstained"] is True


def test_energy_only_query_abstains():
    # "loud" sets an energy target but gives no genre or mood to match on
    assert judge_a("something loud", SONGS)["abstained"] is True


def test_negated_mood_alone_abstains():
    assert judge_a("not sad please", SONGS)["abstained"] is True


def test_k_limits_the_ranking():
    assert len(judge_a("jazz", SONGS, k=3)["ranking"]) == 3
