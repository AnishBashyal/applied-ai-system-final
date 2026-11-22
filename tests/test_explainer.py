import json

import pytest

from src import explainer, gemini_client
from src.gemini_client import GeminiError

SONG = {"id": 1, "title": "Rain Song", "genre": "lofi", "mood": "chill",
        "description": "quiet acoustic lofi with gentle rain sounds"}
SONGS = {1: SONG}
NOTES = {"genres": {"lofi": "Lofi uses slow relaxed beats."}, "moods": {"chill": "A chill mood means relaxed music."}}
PICKS = [{"id": 1, "title": "Rain Song"}]


def reply(monkeypatch, payload):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr(gemini_client, "generate_text", lambda prompt, json_schema=None: text)


def run():
    return explainer.explain("rainy day", PICKS, SONGS, NOTES)[0]


def test_grounded_explanation_is_kept(monkeypatch):
    reply(monkeypatch, [{"title": "Rain Song", "explanation": "Calm rain sounds.", "quote": "gentle rain sounds"}])
    result = run()
    assert result["source"] == "gemini" and result["explanation"] == "Calm rain sounds."


def test_quote_from_the_genre_note_counts_as_grounded(monkeypatch):
    reply(monkeypatch, [{"title": "Rain Song", "explanation": "Slow beats.", "quote": "slow relaxed beats"}])
    assert run()["source"] == "gemini"


def test_quote_check_ignores_case(monkeypatch):
    reply(monkeypatch, [{"title": "Rain Song", "explanation": "x", "quote": "GENTLE RAIN SOUNDS"}])
    assert run()["source"] == "gemini"


def test_invented_quote_falls_back_to_the_retrieved_description(monkeypatch):
    reply(monkeypatch, [{"title": "Rain Song", "explanation": "Great drums.", "quote": "thunderous live drums"}])
    result = run()
    assert result["source"] == "retrieved" and result["explanation"] == SONG["description"]


def test_too_short_quote_does_not_count(monkeypatch):
    reply(monkeypatch, [{"title": "Rain Song", "explanation": "x", "quote": "rain"}])
    assert run()["source"] == "retrieved"


def test_gemini_failure_falls_back(monkeypatch):
    def broken(prompt, json_schema=None):
        raise GeminiError("down")

    monkeypatch.setattr(gemini_client, "generate_text", broken)
    assert run()["source"] == "retrieved"


def test_malformed_reply_falls_back(monkeypatch):
    reply(monkeypatch, "not json at all")
    assert run()["source"] == "retrieved"


def test_song_missing_from_the_reply_falls_back(monkeypatch):
    reply(monkeypatch, [{"title": "Other Song", "explanation": "x", "quote": "gentle rain sounds"}])
    assert run()["source"] == "retrieved"


def test_prompt_contains_only_retrieved_material(monkeypatch):
    seen = {}

    def capture(prompt, json_schema=None):
        seen["prompt"] = prompt
        return "[]"

    monkeypatch.setattr(gemini_client, "generate_text", capture)
    run()
    assert "gentle rain sounds" in seen["prompt"] and "Lofi uses slow relaxed beats" in seen["prompt"]
    assert "rainy day" in seen["prompt"]
