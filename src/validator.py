"""
Input guardrail: runs before either judge.

Cleans the request and rejects input that cannot be a music request, so bad
input never reaches the parser, Gemini or the explainer. Every rejection comes
with a plain reason that the pipeline logs and shows to the user.
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("tastematch.validator")

MIN_LETTERS = 3
MAX_LENGTH = 200
MIN_LETTER_SHARE = 0.5  # letters as a share of non-space characters

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


@dataclass
class ValidationResult:
    ok: bool
    query: str   # the cleaned text, empty when rejected
    reason: str  # why it was rejected, empty when ok


def _reject(reason: str) -> ValidationResult:
    logger.warning("input rejected: %s", reason)
    return ValidationResult(ok=False, query="", reason=reason)


def validate_query(raw) -> ValidationResult:
    """Clean a request and decide whether it can go on to the judges."""
    if not isinstance(raw, str):
        return _reject("request must be text")

    # drop control characters, collapse whitespace
    cleaned = " ".join(_CONTROL_CHARS.sub(" ", raw).split())

    if not cleaned:
        return _reject("request is empty")
    if len(cleaned) > MAX_LENGTH:
        return _reject(f"request is too long ({len(cleaned)} characters, limit {MAX_LENGTH})")

    letters = sum(ch.isalpha() for ch in cleaned)
    if letters < MIN_LETTERS:
        return _reject("request has too few letters to be a music request")
    if letters / len(cleaned.replace(" ", "")) < MIN_LETTER_SHARE:
        return _reject("request is mostly numbers or symbols")

    return ValidationResult(ok=True, query=cleaned, reason="")
