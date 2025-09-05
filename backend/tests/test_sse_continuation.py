import asyncio
import json
import uuid
from types import SimpleNamespace

import pytest

# We test the internal generator directly for precise control
from app.api.v1.chat import send as send_module


class FakeAsyncSession:
    def add(self, obj):
        return None

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def rollback(self):
        return None


def make_sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def sse_token(delta: str, run_id: str = "run_test", seq: int = 1) -> str:
    return make_sse(
        "token",
        {
            "type": "token",
            "run_id": run_id,
            "seq": seq,
            "data": {"delta": delta},
            "timestamp": 0,
        },
    )


def sse_tool_result() -> str:
    return make_sse(
        "tool_result",
        {
            "type": "tool_result",
            "run_id": "run_test",
            "seq": 0,
            "data": {"ok": True},
            "timestamp": 0,
        },
    )


def sse_start(model: str = "gpt-default") -> str:
    return make_sse(
        "start",
        {
            "conversation_id": str(uuid.uuid4()),
            "mode": "green",
            "model": model,
        },
    )


def sse_done_upstream(final_text: str, initial: int, continuation: int) -> str:
    return make_sse(
        "done",
        {
            "type": "done",
            "run_id": "run_test",
            "seq": 0,
            "data": {
                "final_text": final_text,
                "tool_calls_count": 0,
                "token_counts": {
                    "initial": initial,
                    "continuation": continuation,
                },
            },
            "timestamp": 0,
        },
    )


def sse_error_retryable(message: str = "retry", retryable: bool = True) -> str:
    return make_sse(
        "error",
        {
            "type": "error",
            "run_id": "run_test",
            "seq": 0,
            "data": {
                "error": message,
                "error_type": "test_error",
                "retryable": retryable,
            },
            "timestamp": 0,
        },
    )


async def collect_events(async_gen):
    events = []
    async for item in async_gen:
        events.append(item)
    return events


def parse_event_name(evt: str) -> str:
    return evt.split("\n", 1)[0].split(": ")[1]


def parse_event_payload(evt: str) -> dict:
    data_line = evt.split("\ndata: ")[1].split("\n")[0]
    return json.loads(data_line)


@pytest.mark.asyncio
async def test_normal_continuation_token_after_tool_result(monkeypatch):
    # Arrange: stub out DB history and openai service streaming
    async def fake_load_history(*args, **kwargs):
        return []
    monkeypatch.setattr(send_module, "load_message_history", fake_load_history)

    # Build a stub service that yields: start -> tool_result -> token -> upstream done
    class StubService:
        async def stream_responses(self, **kwargs):
            yield sse_start()
            yield sse_tool_result()
            yield sse_token("Hello world", seq=1)
            yield sse_done_upstream(final_text="ignored upstream", initial=1, continuation=1)

    monkeypatch.setattr(send_module, "openai_service", StubService())

    # Speed up retries if triggered (shouldn't be for this test)
    async def fast_sleep(_):
        return None

    monkeypatch.setattr(send_module.asyncio, "sleep", fast_sleep)

    # Configure settings to avoid fallback switching here
    send_module.settings.SSE_MAX_STREAM_RETRIES = 0
    send_module.settings.SSE_USE_MODEL_FALLBACK = False

    conversation = SimpleNamespace(
        id=uuid.uuid4(), mode="green", meta_data=None, user_id=uuid.uuid4()
    )
    user = SimpleNamespace(id=uuid.uuid4())
    db = FakeAsyncSession()

    # Act
    gen = send_module.sse_generator("hello", conversation, db, user, request=None)
    out_events = await collect_events(gen)

    # Assert: ensure token after tool_result before final done
    names = [parse_event_name(e) for e in out_events]
    assert names.count("done") == 1
    assert "tool_result" in names
    # Find positions
    tool_idx = names.index("tool_result")
    # There should be a token after tool_result before done
    assert any(n == "token" for n in names[tool_idx + 1 : names.index("done")])

    # Validate final done payload has instrumentation fields
    final_done_evt = out_events[names.index("done")]
    payload = parse_event_payload(final_done_evt)
    data = payload["data"]
    assert "final_text" in data
    assert "token_counts" in data
    assert "event_timeline" in data
    assert "fallback_used" in data
    assert "model_used" in data
    assert "retry_stats" in data


@pytest.mark.asyncio
async def test_zero_continuation_uses_upstream_final_text_fallback(monkeypatch):
    # Arrange
    async def fake_load_history(*args, **kwargs):
        return []
    monkeypatch.setattr(send_module, "load_message_history", fake_load_history)

    class StubService:
        async def stream_responses(self, **kwargs):
            yield sse_start()
            yield sse_tool_result()
            # No tokens after tool_result
            yield sse_done_upstream(final_text="Upstream final", initial=2, continuation=0)

    monkeypatch.setattr(send_module, "openai_service", StubService())

    async def fast_sleep(_):
        return None

    monkeypatch.setattr(send_module.asyncio, "sleep", fast_sleep)

    send_module.settings.SSE_MAX_STREAM_RETRIES = 0
    send_module.settings.SSE_USE_MODEL_FALLBACK = False

    conversation = SimpleNamespace(
        id=uuid.uuid4(), mode="green", meta_data=None, user_id=uuid.uuid4()
    )
    user = SimpleNamespace(id=uuid.uuid4())
    db = FakeAsyncSession()

    # Act
    gen = send_module.sse_generator("hello", conversation, db, user, request=None)
    out_events = await collect_events(gen)

    names = [parse_event_name(e) for e in out_events]
    assert names.count("done") == 1
    # Ensure there is no token after tool_result
    tool_idx = names.index("tool_result")
    assert not any(n == "token" for n in names[tool_idx + 1 : names.index("done")])

    final_done_evt = out_events[names.index("done")]
    payload = parse_event_payload(final_done_evt)
    data = payload["data"]
    assert data["final_text"] == "Upstream final"
    assert data["token_counts"]["continuation"] == 0
    assert data["fallback_used"] is True


@pytest.mark.asyncio
async def test_retry_schedule_and_model_switch_then_success(monkeypatch):
    # Arrange
    async def fake_load_history(*args, **kwargs):
        return []
    monkeypatch.setattr(send_module, "load_message_history", fake_load_history)

    class StubService:
        def __init__(self):
            self.calls = 0

        async def stream_responses(self, **kwargs):
            # First call: emit retryable error after start
            if self.calls == 0:
                self.calls += 1
                yield sse_start(model=send_module.settings.MODEL_DEFAULT)
                yield sse_error_retryable("temporary")
            else:
                # Second call: emit token and upstream done
                self.calls += 1
                yield sse_start(model=send_module.settings.MODEL_FALLBACK)
                yield sse_token("Hi after retry", seq=1)
                yield sse_done_upstream(final_text="ignored", initial=0, continuation=1)

    stub = StubService()
    monkeypatch.setattr(send_module, "openai_service", stub)

    # Speed up sleep
    async def fast_sleep(_):
        return None

    monkeypatch.setattr(send_module.asyncio, "sleep", fast_sleep)

    # Configure settings for one retry and fallback model
    send_module.settings.SSE_MAX_STREAM_RETRIES = 1
    send_module.settings.SSE_RETRY_BACKOFF_BASE_MS = 1
    send_module.settings.SSE_RETRY_JITTER_MS = 0
    send_module.settings.SSE_RETRY_BACKOFF_MAX_MS = 5
    send_module.settings.SSE_USE_MODEL_FALLBACK = True
    send_module.settings.MODEL_DEFAULT = "gpt-default"
    send_module.settings.MODEL_FALLBACK = "gpt-fallback"

    conversation = SimpleNamespace(
        id=uuid.uuid4(), mode="green", meta_data=None, user_id=uuid.uuid4()
    )
    user = SimpleNamespace(id=uuid.uuid4())
    db = FakeAsyncSession()

    # Act
    gen = send_module.sse_generator("hello", conversation, db, user, request=None)
    out_events = await collect_events(gen)

    # Assert info events for retry scheduling and model switch
    info_events = [e for e in out_events if parse_event_name(e) == "info"]
    assert any(parse_event_payload(e)["data"].get("info_type") == "retry_scheduled" for e in info_events)
    assert any(parse_event_payload(e)["data"].get("info_type") == "model_switch" for e in info_events)

    # Final done should reflect fallback model usage and attempts=2
    names = [parse_event_name(e) for e in out_events]
    final_done_evt = out_events[names.index("done")]
    payload = parse_event_payload(final_done_evt)
    data = payload["data"]
    assert data["model_used"] == send_module.settings.MODEL_FALLBACK
    assert data["retry_stats"]["attempts"] == 2
    assert data["retry_stats"]["used_fallback_model"] is True


@pytest.mark.asyncio
async def test_non_retryable_error_no_retry_emits_final_error(monkeypatch):
    # Arrange
    async def fake_load_history(*args, **kwargs):
        return []
    monkeypatch.setattr(send_module, "load_message_history", fake_load_history)

    class StubService:
        async def stream_responses(self, **kwargs):
            # Emit start then a non-retryable error
            yield sse_start()
            yield sse_error_retryable("fatal", retryable=False)

    monkeypatch.setattr(send_module, "openai_service", StubService())

    async def fast_sleep(_):
        return None
    monkeypatch.setattr(send_module.asyncio, "sleep", fast_sleep)

    # Allow many retries, but since error is non-retryable there should be none
    send_module.settings.SSE_MAX_STREAM_RETRIES = 3
    send_module.settings.SSE_USE_MODEL_FALLBACK = True

    conversation = SimpleNamespace(
        id=uuid.uuid4(), mode="green", meta_data=None, user_id=uuid.uuid4()
    )
    user = SimpleNamespace(id=uuid.uuid4())
    db = FakeAsyncSession()

    # Act
    gen = send_module.sse_generator("hello", conversation, db, user, request=None)
    out_events = await collect_events(gen)

    # Assert: there should be exactly one error forwarded (final), and no retry infos
    names = [parse_event_name(e) for e in out_events]
    assert names[0] == "message_created"
    assert names.count("start") == 1
    assert names.count("info") == 0
    assert names.count("done") == 0
    assert names.count("error") == 1

    final_error_evt = out_events[names.index("error")]
    payload = parse_event_payload(final_error_evt)
    data = payload["data"]
    assert data["error"] == "fatal"
    assert data["retryable"] is False
    assert data["attempts"] == 1


@pytest.mark.asyncio
async def test_retry_exhaustion_with_fallback_and_final_error(monkeypatch):
    # Arrange
    async def fake_load_history(*args, **kwargs):
        return []
    monkeypatch.setattr(send_module, "load_message_history", fake_load_history)

    class StubService:
        def __init__(self):
            self.calls = 0

        async def stream_responses(self, **kwargs):
            self.calls += 1
            # Always emit start then retryable error
            yield sse_start(model=kwargs.get("model_override") or send_module.settings.MODEL_DEFAULT)
            yield sse_error_retryable("temporary", retryable=True)

    stub = StubService()
    monkeypatch.setattr(send_module, "openai_service", stub)

    async def fast_sleep(_):
        return None
    monkeypatch.setattr(send_module.asyncio, "sleep", fast_sleep)

    send_module.settings.SSE_MAX_STREAM_RETRIES = 2
    send_module.settings.SSE_RETRY_BACKOFF_BASE_MS = 1
    send_module.settings.SSE_RETRY_JITTER_MS = 0
    send_module.settings.SSE_RETRY_BACKOFF_MAX_MS = 5
    send_module.settings.SSE_USE_MODEL_FALLBACK = True
    send_module.settings.MODEL_DEFAULT = "gpt-default"
    send_module.settings.MODEL_FALLBACK = "gpt-fallback"

    conversation = SimpleNamespace(
        id=uuid.uuid4(), mode="green", meta_data=None, user_id=uuid.uuid4()
    )
    user = SimpleNamespace(id=uuid.uuid4())
    db = FakeAsyncSession()

    # Act
    gen = send_module.sse_generator("hello", conversation, db, user, request=None)
    out_events = await collect_events(gen)

    # Assert: 2 retry_scheduled infos, 1 model_switch info, only one start forwarded, final error
    names = [parse_event_name(e) for e in out_events]
    assert names[0] == "message_created"
    assert names.count("start") == 1
    info_payloads = [parse_event_payload(e)["data"] for e in out_events if parse_event_name(e) == "info"]
    assert sum(1 for d in info_payloads if d.get("info_type") == "retry_scheduled") == 2
    # Model switch info is emitted on each attempt after the first when still no tokens (attempts 2 and 3 here)
    assert sum(1 for d in info_payloads if d.get("info_type") == "model_switch") == 2
    assert names.count("done") == 0
    assert names.count("error") == 1

    final_error_evt = out_events[names.index("error")]
    payload = parse_event_payload(final_error_evt)
    data = payload["data"]
    assert data["error"] == "temporary"
    assert data["retryable"] is False
    # attempts should be max_retries + 1 (3 attempts total)
    assert data["attempts"] == 3


@pytest.mark.asyncio
async def test_no_retry_after_tokens_then_error(monkeypatch):
    # Arrange
    async def fake_load_history(*args, **kwargs):
        return []
    monkeypatch.setattr(send_module, "load_message_history", fake_load_history)

    class StubService:
        async def stream_responses(self, **kwargs):
            yield sse_start()
            yield sse_token("partial", seq=1)
            # Error after some tokens -> should not retry
            yield sse_error_retryable("midstream failure", retryable=True)

    monkeypatch.setattr(send_module, "openai_service", StubService())

    async def fast_sleep(_):
        return None
    monkeypatch.setattr(send_module.asyncio, "sleep", fast_sleep)

    send_module.settings.SSE_MAX_STREAM_RETRIES = 2
    send_module.settings.SSE_RETRY_JITTER_MS = 0
    send_module.settings.SSE_USE_MODEL_FALLBACK = True

    conversation = SimpleNamespace(
        id=uuid.uuid4(), mode="green", meta_data=None, user_id=uuid.uuid4()
    )
    user = SimpleNamespace(id=uuid.uuid4())
    db = FakeAsyncSession()

    # Act
    gen = send_module.sse_generator("hello", conversation, db, user, request=None)
    out_events = await collect_events(gen)

    # Assert: error without any retry info
    names = [parse_event_name(e) for e in out_events]
    assert names.count("start") == 1
    assert names.count("info") == 0
    assert names.count("done") == 0
    assert names.count("token") >= 1
    assert names.count("error") == 1

    final_error_evt = out_events[names.index("error")]
    payload = parse_event_payload(final_error_evt)
    data = payload["data"]
    assert data["error"] == "midstream failure"
    assert data["attempts"] == 1
