from src.recommender import load_songs, recommend_songs
from src.text_parser import parse_query


def test_study_query_gets_low_energy_and_focus_or_chill_mood():
    prefs = parse_query("mellow music for studying late at night")
    assert prefs["energy"] < 0.4
    assert prefs["mood"] in ("chill", "focused")
    assert prefs["recognised"]


def test_genre_is_read_from_text():
    assert parse_query("some hard rock")["genre"] == "rock"


def test_longer_phrase_wins_over_shorter_word():
    # "indie pop" must not also count as "pop"
    prefs = parse_query("indie pop")
    assert prefs["genre"] == "indie pop"
    assert prefs["matched"] == ["indie pop"]


def test_workout_query_gets_high_energy():
    prefs = parse_query("gym workout")
    assert prefs["energy"] > 0.85
    assert prefs["mood"] == "intense"


def test_acoustic_only_set_when_mentioned():
    assert "likes_acoustic" not in parse_query("happy pop")
    assert parse_query("acoustic guitar")["likes_acoustic"] is True


def test_negated_mood_is_ignored():
    assert parse_query("not sad please")["mood"] is None


def test_negation_allows_one_word_between():
    assert parse_query("not too sad")["mood"] is None


def test_unknown_text_is_not_recognised():
    prefs = parse_query("asdf qwerty")
    assert prefs["recognised"] is False
    assert prefs["matched"] == []
    assert prefs["energy"] == 0.5


def test_vibe_words_outside_the_lexicon_are_not_recognised():
    # known weakness of Judge A: vibe words it has never seen
    assert parse_query("cozy rainy afternoon")["recognised"] is False


def test_matched_terms_have_no_duplicates():
    matched = parse_query("intense gym workout rock")["matched"]
    assert len(matched) == len(set(matched))


def test_parsed_prefs_work_with_the_original_scorer():
    songs = load_songs("data/songs.csv")
    top = recommend_songs(parse_query("calm acoustic folk"), songs, k=1)[0][0]
    assert top["genre"] == "folk"
