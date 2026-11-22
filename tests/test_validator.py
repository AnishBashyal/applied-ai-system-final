import logging

from src.validator import MAX_LENGTH, validate_query


def test_normal_request_passes_unchanged():
    result = validate_query("mellow music for studying")
    assert result.ok and result.query == "mellow music for studying" and result.reason == ""


def test_whitespace_is_collapsed_and_trimmed():
    assert validate_query("  chill   lofi \n beats  ").query == "chill lofi beats"


def test_control_characters_are_removed():
    assert validate_query("happy\x00 pop\x1b music").query == "happy pop music"


def test_empty_and_blank_are_rejected():
    for text in ("", "   ", "\n\t"):
        result = validate_query(text)
        assert not result.ok and "empty" in result.reason


def test_non_text_is_rejected():
    for value in (None, 42, ["jazz"]):
        result = validate_query(value)
        assert not result.ok and "text" in result.reason


def test_too_long_is_rejected():
    result = validate_query("a" * (MAX_LENGTH + 1))
    assert not result.ok and "too long" in result.reason


def test_exactly_the_limit_is_allowed():
    assert validate_query("a" * MAX_LENGTH).ok


def test_numbers_and_symbols_only_are_rejected():
    for text in ("12345", "!!! ???", "$$ 99 ##"):
        assert not validate_query(text).ok


def test_mostly_symbols_is_rejected():
    result = validate_query("abc #### 1234 !!!")
    assert not result.ok and "numbers or symbols" in result.reason


def test_a_few_digits_in_a_real_request_are_fine():
    assert validate_query("best 90s rock").ok


def test_non_english_letters_count_as_letters():
    assert validate_query("música relajante").ok


def test_gibberish_made_of_letters_passes_on_purpose():
    # the validator only checks shape; meaningless letters are caught later by the judges
    assert validate_query("asdf qwerty").ok


def test_rejections_are_logged(caplog):
    with caplog.at_level(logging.WARNING, logger="tastematch.validator"):
        validate_query("")
    assert "input rejected" in caplog.text
