import json

import numpy as np
import pytest

from src import gemini_client, pipeline
from src.gemini_client import GeminiError


def fake_b(titles, strength=0.15):
    songs = {s["title"]: s for s in pipeline.load_songs("data/songs.csv")}
    return {"judge": "B", "abstained": False, "strength": strength, "reason": "ranked",
            "ranking": [{"id": songs[t]["id"], "title": t, "score": 0.8, "why": f"{t} description"} for t in titles]}


LOFI = ["Library Rain", "Midnight Coding", "Focus Flow", "Deep Work Drift", "Late Bus Home"]


@pytest.fixture
def make(monkeypatch, tmp_path):
    """Build a pipeline with a fake index, a scripted Judge B and a Gemini that always fails."""
    def build(judge_b_result=None, index_ok=True):
        monkeypatch.setattr(pipeline, "build_index", lambda songs: np.zeros((36, 2)))
        if not index_ok:
            def no_index(songs):
                raise GeminiError("no key")
            monkeypatch.setattr(pipeline, "build_index", no_index)
        monkeypatch.setattr(pipeline, "judge_b", lambda q, s, i, k=5: judge_b_result)

        def down(prompt, json_schema=None):
            raise GeminiError("down")
        monkeypatch.setattr(gemini_client, "generate_text", down)
        return pipeline.Pipeline(run_log=str(tmp_path / "runs.jsonl")), tmp_path / "runs.jsonl"
    return build


def test_empty_input_is_rejected_and_logged(make):
    p, log = make(fake_b(LOFI))
    result = p.run("   ")
    assert result["status"] == "rejected" and "empty" in result["message"]
    assert json.loads(log.read_text().splitlines()[-1])["status"] == "rejected"


def test_agreeing_judges_give_an_ok_answer_with_explanations(make):
    p, _ = make(fake_b(LOFI))
    result = p.run("chill lofi for studying")
    assert result["status"] == "ok" and result["confidence"] >= 0.4
    assert len(result["picks"]) == 5
    assert all(pick["explanation"] for pick in result["picks"])


def test_explanations_fall_back_to_retrieved_text_when_gemini_is_down(make):
    p, _ = make(fake_b(LOFI))
    picks = p.run("chill lofi for studying")["picks"]
    assert all(pick["explained_by"] == "retrieved" for pick in picks)


def test_nonsense_is_refused(make):
    p, _ = make(fake_b(LOFI, strength=0.03))
    result = p.run("asdf qwerty")
    assert result["status"] == "refused" and result["picks"] == []


def test_keywordless_vibe_request_gets_a_warning(make):
    p, _ = make(fake_b(LOFI, strength=0.15))
    result = p.run("cozy rainy afternoon")
    assert result["status"] == "warning" and result["confidence"] <= 0.5
    assert "one judge" in result["warning"]


def test_without_an_index_judge_a_still_answers(make):
    p, _ = make(index_ok=False)
    result = p.run("chill lofi for studying")
    assert result["status"] == "warning" and "keyword judge" in result["message"]


def test_each_run_adds_one_parseable_log_line(make):
    p, log = make(fake_b(LOFI))
    p.run("chill lofi for studying")
    p.run("")
    records = [json.loads(line) for line in log.read_text().splitlines()]
    assert [r["status"] for r in records] == ["ok", "rejected"]
    assert records[0]["judge_a"]["abstained"] is False and records[0]["overlap"] is not None


def test_log_failure_does_not_stop_the_run(make, tmp_path):
    p, _ = make(fake_b(LOFI))
    p.run_log = str(tmp_path)  # a directory, so writing fails
    assert p.run("chill lofi for studying")["status"] == "ok"
