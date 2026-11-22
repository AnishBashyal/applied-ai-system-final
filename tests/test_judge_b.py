import numpy as np
import pytest

from src import gemini_client, judge_b as jb
from src.gemini_client import GeminiError

SONGS = [
    {"id": 1, "title": "Rain Song", "description": "quiet rain"},
    {"id": 2, "title": "Punk Song", "description": "loud punk"},
    {"id": 3, "title": "Party Song", "description": "dance party"},
]
VECTORS = {"quiet rain": [1.0, 0.0], "loud punk": [0.0, 1.0], "dance party": [0.6, 0.8]}


@pytest.fixture
def fake_embed(monkeypatch):
    calls = []

    def embed(texts):
        calls.append(list(texts))
        return [VECTORS[t] if t in VECTORS else [0.9, 0.1] for t in texts]

    monkeypatch.setattr(gemini_client, "embed_texts", embed)
    return calls


def test_index_rows_are_unit_length(fake_embed, tmp_path):
    index = jb.build_index(SONGS, cache_path=str(tmp_path / "c.json"))
    assert index.shape == (3, 2)
    assert np.allclose(np.linalg.norm(index, axis=1), 1.0)


def test_second_build_uses_the_cache(fake_embed, tmp_path):
    cache = str(tmp_path / "c.json")
    jb.build_index(SONGS, cache_path=cache)
    jb.build_index(SONGS, cache_path=cache)
    assert len(fake_embed) == 1  # only the first build called Gemini


def test_only_new_descriptions_are_embedded(fake_embed, tmp_path):
    cache = str(tmp_path / "c.json")
    jb.build_index(SONGS[:2], cache_path=cache)
    jb.build_index(SONGS, cache_path=cache)
    assert fake_embed[1] == ["dance party"]


def test_corrupt_cache_is_rebuilt(fake_embed, tmp_path):
    cache = tmp_path / "c.json"
    cache.write_text("{not json")
    assert jb.build_index(SONGS, cache_path=str(cache)).shape == (3, 2)


def test_most_similar_song_ranks_first(fake_embed, tmp_path):
    index = jb.build_index(SONGS, cache_path=str(tmp_path / "c.json"))
    result = jb.judge_b("rainy", SONGS, index, k=3)  # fake vector [0.9, 0.1] is closest to rain
    assert result["abstained"] is False
    assert [r["title"] for r in result["ranking"]][0] == "Rain Song"
    scores = [r["score"] for r in result["ranking"]]
    assert scores == sorted(scores, reverse=True)


def test_k_limits_the_ranking(fake_embed, tmp_path):
    index = jb.build_index(SONGS, cache_path=str(tmp_path / "c.json"))
    assert len(jb.judge_b("rainy", SONGS, index, k=2)["ranking"]) == 2


def test_reason_quotes_the_retrieved_description(fake_embed, tmp_path):
    index = jb.build_index(SONGS, cache_path=str(tmp_path / "c.json"))
    assert '"quiet rain"' in jb.judge_b("rainy", SONGS, index, k=1)["ranking"][0]["why"]


def test_judge_b_abstains_when_gemini_fails(fake_embed, tmp_path, monkeypatch):
    index = jb.build_index(SONGS, cache_path=str(tmp_path / "c.json"))

    def broken(texts):
        raise GeminiError("down")

    monkeypatch.setattr(gemini_client, "embed_texts", broken)
    result = jb.judge_b("rainy", SONGS, index)
    assert result["abstained"] is True
    assert result["ranking"] == []
    assert "down" in result["reason"]


def test_strength_is_top_similarity_minus_catalog_average(fake_embed, tmp_path):
    index = jb.build_index(SONGS, cache_path=str(tmp_path / "c.json"))
    result = jb.judge_b("rainy", SONGS, index, k=3)
    vector = np.array([0.9, 0.1]) / np.linalg.norm([0.9, 0.1])
    sims = index @ vector
    assert result["strength"] == pytest.approx(sims.max() - sims.mean(), abs=1e-3)
