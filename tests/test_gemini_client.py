import pytest

from src import gemini_client
from src.gemini_client import GeminiError


class ApiError(Exception):
    def __init__(self, code):
        self.code = code


class APITimeoutError(Exception):
    pass


class FakeResult:
    def __init__(self, text=None, values=None):
        self.text = text
        self.embeddings = [type("E", (), {"values": values})()] if values else None


class FakeModels:
    """Replays a list of outcomes: an exception is raised, anything else is returned."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def _next(self):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def generate_content(self, **kwargs):
        return self._next()

    def embed_content(self, **kwargs):
        return self._next()


class FakeClient:
    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(gemini_client, "BACKOFF_SECONDS", 0)


def use(monkeypatch, outcomes):
    client = FakeClient(outcomes)
    monkeypatch.setattr(gemini_client, "get_client", lambda: client)
    return client


def test_missing_key_raises_a_clear_error(monkeypatch):
    monkeypatch.setattr(gemini_client, "_client", None)
    monkeypatch.setattr(gemini_client, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(GeminiError, match="GEMINI_API_KEY"):
        gemini_client.get_client()


def test_generate_text_returns_the_reply(monkeypatch):
    use(monkeypatch, [FakeResult(text="  ok  ")])
    assert gemini_client.generate_text("hi") == "ok"


def test_empty_reply_is_an_error(monkeypatch):
    use(monkeypatch, [FakeResult(text="")])
    with pytest.raises(GeminiError, match="empty"):
        gemini_client.generate_text("hi")


def test_transient_error_is_retried_then_succeeds(monkeypatch):
    client = use(monkeypatch, [ApiError(503), ApiError(429), FakeResult(text="ok")])
    assert gemini_client.generate_text("hi") == "ok"
    assert client.models.calls == 3


def test_timeout_is_retried(monkeypatch):
    client = use(monkeypatch, [APITimeoutError(), FakeResult(text="ok")])
    assert gemini_client.generate_text("hi") == "ok"
    assert client.models.calls == 2


def test_gives_up_after_max_attempts(monkeypatch):
    client = use(monkeypatch, [ApiError(503)] * gemini_client.MAX_ATTEMPTS)
    with pytest.raises(GeminiError, match="after 3 attempts"):
        gemini_client.generate_text("hi")
    assert client.models.calls == gemini_client.MAX_ATTEMPTS


def test_permanent_error_is_not_retried(monkeypatch):
    client = use(monkeypatch, [ApiError(404), FakeResult(text="ok")])
    with pytest.raises(GeminiError):
        gemini_client.generate_text("hi")
    assert client.models.calls == 1


def test_embed_texts_returns_one_vector_per_text(monkeypatch):
    client = use(monkeypatch, [FakeResult(values=[0.1, 0.2]), FakeResult(values=[0.3, 0.4])])
    assert gemini_client.embed_texts(["a", "b"]) == [[0.1, 0.2], [0.3, 0.4]]
    assert client.models.calls == 2


def test_embed_texts_with_no_input_makes_no_calls(monkeypatch):
    client = use(monkeypatch, [])
    assert gemini_client.embed_texts([]) == []
    assert client.models.calls == 0
