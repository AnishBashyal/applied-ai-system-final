"""
Thin wrapper around the Gemini API.

Everything that talks to Gemini goes through this file, so there is one place
that loads the key, retries flaky calls and turns failures into one clear error.
The key is read from the GEMINI_API_KEY environment variable (or a local .env
file) and is never printed or logged.
"""

import logging
import os
import time
from typing import Dict, List, Optional

from dotenv import load_dotenv

logger = logging.getLogger("tastematch.gemini")

TEXT_MODEL = "gemini-3.5-flash-lite"
EMBED_MODEL = "gemini-embedding-2"
EMBED_DIMENSIONS = 768
REQUEST_TIMEOUT_MS = 30_000

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 1.0
# HTTP-style codes worth retrying: rate limit and temporary server trouble
TRANSIENT_CODES = {429, 500, 502, 503, 504}

_client = None


class GeminiError(Exception):
    """Raised when Gemini cannot be used or a call keeps failing."""


def get_client():
    """Create the Gemini client once, or raise GeminiError if there is no key."""
    global _client
    if _client is not None:
        return _client

    load_dotenv(".env")
    if not os.environ.get("GEMINI_API_KEY"):
        raise GeminiError("GEMINI_API_KEY is not set (see .env.example)")

    from google import genai
    from google.genai import types
    _client = genai.Client(http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS))
    return _client


def _call_with_retry(label: str, fn):
    """Run fn(), retrying transient failures a few times before giving up."""
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except GeminiError:
            raise
        except Exception as error:  # the SDK raises several error types
            last_error = error
            code = getattr(error, "code", None)
            timed_out = "timeout" in type(error).__name__.lower()
            if code not in TRANSIENT_CODES and not timed_out:
                logger.error("%s failed (not retrying): %s", label, type(error).__name__)
                raise GeminiError(f"{label} failed: {type(error).__name__}") from error
            logger.warning("%s attempt %d/%d failed (%s)", label, attempt, MAX_ATTEMPTS, code or type(error).__name__)
            if attempt < MAX_ATTEMPTS:
                time.sleep(BACKOFF_SECONDS * attempt)
    raise GeminiError(f"{label} failed after {MAX_ATTEMPTS} attempts") from last_error


def generate_text(prompt: str, json_schema: Optional[Dict] = None) -> str:
    """Send a prompt and return the text of the reply.

    Pass json_schema to ask for JSON output that follows that schema.
    """
    client = get_client()
    config = {}
    if json_schema is not None:
        config = {"response_mime_type": "application/json", "response_json_schema": json_schema}
    result = _call_with_retry(
        "generate_text",
        lambda: client.models.generate_content(model=TEXT_MODEL, contents=prompt, config=config),
    )
    text = (result.text or "").strip()
    if not text:
        raise GeminiError("generate_text returned an empty reply")
    return text


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Return one embedding vector per input text.

    gemini-embedding-2 merges a list of inputs into a single vector, so each
    text is embedded in its own call to get one vector per text.
    """
    client = get_client()
    vectors = []
    for text in texts:
        result = _call_with_retry(
            "embed_texts",
            lambda t=text: client.models.embed_content(
                model=EMBED_MODEL,
                contents=t,
                config={"output_dimensionality": EMBED_DIMENSIONS},
            ),
        )
        vectors.append(list(result.embeddings[0].values))
    return vectors
