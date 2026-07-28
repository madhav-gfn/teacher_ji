from __future__ import annotations

from agents import reflection


def _base_state(**overrides):
    state = {
        "retrieved_context": [{"text": "chunk", "chapter_title": "Fractions", "chapter_num": "5", "page_start": 1, "score": 0.1}],
        "teaching_output": {"headline": "Fractions", "explanation": "..."},
        "topic": "Fractions",
        "chapter": "Fractions",
        "grade": 6,
        "teaching_agent": "math_agent",
        "reflection_retry_count": 0,
    }
    state.update(overrides)
    return state


def test_reflection_skips_llm_call_when_no_context(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("call_groq_with_retry should not be called when there is nothing to audit")

    monkeypatch.setattr(reflection, "call_groq_with_retry", boom)
    result = reflection.reflection_agent(_base_state(retrieved_context=[]))

    assert result["reflection_next"] == "accept"
    assert result["reflection_retry_count"] == 0


def test_reflection_accepts_when_passed(monkeypatch):
    monkeypatch.setattr(reflection, "call_groq_with_retry", lambda *a, **k: {"passed": True})
    result = reflection.reflection_agent(_base_state())
    assert result["reflection_next"] == "accept"
    assert result["teaching_reflection"] == {}


def test_reflection_retries_once_on_first_failure(monkeypatch):
    monkeypatch.setattr(
        reflection,
        "call_groq_with_retry",
        lambda *a, **k: {"passed": False, "critique": "not grounded in the retrieved chunk"},
    )
    result = reflection.reflection_agent(_base_state(reflection_retry_count=0))

    assert result["reflection_next"] == "retry"
    assert result["reflection_retry_count"] == 1
    assert result["teaching_reflection"]["critique"] == "not grounded in the retrieved chunk"


def test_reflection_force_accepts_after_retry_budget_is_spent(monkeypatch):
    monkeypatch.setattr(
        reflection,
        "call_groq_with_retry",
        lambda *a, **k: {"passed": False, "critique": "still not grounded"},
    )
    result = reflection.reflection_agent(_base_state(reflection_retry_count=1))

    assert result["reflection_next"] == "accept"
    assert result["reflection_retry_count"] == 0


def test_reflection_fails_open_when_llm_call_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("groq is down")

    monkeypatch.setattr(reflection, "call_groq_with_retry", boom)
    result = reflection.reflection_agent(_base_state())

    assert result["reflection_next"] == "accept"


def test_route_from_reflection_retry_goes_back_to_the_same_subject_agent():
    state = {"reflection_next": "retry", "teaching_agent": "science_agent"}
    assert reflection.route_from_reflection(state) == "science_agent"


def test_route_from_reflection_accept_goes_to_supervisor():
    assert reflection.route_from_reflection({"reflection_next": "accept"}) == "supervisor"


def test_route_from_reflection_unknown_teaching_agent_falls_back_to_supervisor():
    state = {"reflection_next": "retry", "teaching_agent": "document_tutor"}
    assert reflection.route_from_reflection(state) == "supervisor"
