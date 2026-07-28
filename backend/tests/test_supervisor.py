from __future__ import annotations

import pytest

from agents import supervisor


# ---------------------------------------------------------------------------
# _deterministic_action - mechanical routing that must never invoke the LLM
# ---------------------------------------------------------------------------


def test_deterministic_action_mode_already_complete():
    action = supervisor._deterministic_action({"mode": "complete"})
    assert action[0] == "complete"


def test_deterministic_action_feedback_pending():
    action = supervisor._deterministic_action({"mode": "feedback", "student_answer": "42"})
    assert action[0] == "feedback"


@pytest.mark.parametrize(
    "score,expected_action",
    [(0.9, "complete"), (0.8, "complete"), (0.79, "quiz"), (0.0, "quiz")],
)
def test_deterministic_action_quiz_all_answered(score, expected_action):
    state = {
        "mode": "quiz",
        "quiz_questions": [{"evaluation": {"is_correct": True}}, {"evaluation": {"is_correct": False}}],
        "current_question_index": 2,
        "session_score": score,
    }
    action = supervisor._deterministic_action(state)
    assert action[0] == expected_action


def test_deterministic_action_quiz_not_all_answered_falls_through():
    state = {
        "mode": "quiz",
        "quiz_questions": [{"evaluation": {}}, {}],
        "current_question_index": 1,
    }
    # Not all answered, but quiz_questions already exist -> "already generated"
    # branch takes over deterministically (still no LLM call needed).
    action = supervisor._deterministic_action(state)
    assert action == ("complete", "Quiz already generated and awaiting student answers.")


def test_deterministic_action_teaching_output_already_produced():
    action = supervisor._deterministic_action({"mode": "teaching", "teaching_output": {"headline": "x"}})
    assert action[0] == "complete"


def test_deterministic_action_feedback_output_already_produced():
    action = supervisor._deterministic_action({"mode": "feedback", "feedback_output": {"is_correct": True}})
    assert action[0] == "complete"


def test_deterministic_action_returns_none_when_a_decision_is_needed():
    assert supervisor._deterministic_action({"mode": "teaching"}) is None


# ---------------------------------------------------------------------------
# _eligible_prerequisite_topics
# ---------------------------------------------------------------------------


def test_eligible_prerequisite_topics_filters_correctly():
    prerequisites = [
        {"topic": "Fractions as equal parts", "mastery": 0.2, "already_revised_this_session": False},
        {"topic": "Already Revised", "mastery": 0.1, "already_revised_this_session": True},
        {"topic": "High Mastery", "mastery": 0.9, "already_revised_this_session": False},
        {"topic": "Unassessed", "mastery": "unknown (no prior data)", "already_revised_this_session": False},
    ]
    eligible = supervisor._eligible_prerequisite_topics(prerequisites)
    assert eligible == {"fractions as equal parts"}


# ---------------------------------------------------------------------------
# supervisor_node - the LLM decision path (mocked) and its guardrails
# ---------------------------------------------------------------------------


def test_supervisor_node_shortcuts_deterministic_path_without_calling_llm(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("call_groq_with_retry should not be called on a deterministic turn")

    monkeypatch.setattr(supervisor, "call_groq_with_retry", boom)
    result = supervisor.supervisor_node({"mode": "teaching", "teaching_output": {"headline": "x"}})
    assert result["next_action"] == "complete"


def test_supervisor_node_uses_llm_decision(monkeypatch):
    monkeypatch.setattr(
        supervisor,
        "call_groq_with_retry",
        lambda *a, **k: {"next_action": "teach", "target_topic": "", "reasoning": "student is ready"},
    )
    result = supervisor.supervisor_node({"mode": "teaching", "subject": "math", "topic": "Fractions"})
    assert result["next_action"] == "teach"
    assert result["supervisor_reasoning"] == "student is ready"


def test_supervisor_node_falls_back_when_llm_returns_invalid_action(monkeypatch):
    monkeypatch.setattr(
        supervisor,
        "call_groq_with_retry",
        lambda *a, **k: {"next_action": "hallucinated_action", "reasoning": "??"},
    )
    result = supervisor.supervisor_node({"mode": "teaching", "subject": "math", "topic": "Fractions"})
    assert result["next_action"] == "teach"
    assert "LLM decision unavailable" in result["supervisor_reasoning"]


def test_supervisor_node_falls_back_when_llm_call_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("groq is down")

    monkeypatch.setattr(supervisor, "call_groq_with_retry", boom)
    result = supervisor.supervisor_node({"mode": "quiz", "subject": "math", "topic": "Fractions"})
    assert result["next_action"] == "quiz"
    assert "groq is down" in result["supervisor_reasoning"]


def test_supervisor_node_rejects_ineligible_revise_prerequisite_target(monkeypatch):
    monkeypatch.setattr(
        supervisor,
        "call_groq_with_retry",
        lambda *a, **k: {
            "next_action": "revise_prerequisite",
            "target_topic": "a topic that does not exist",
            "reasoning": "student seems weak",
        },
    )
    state = {"mode": "teaching", "subject": "math", "topic": "Equivalent fractions"}
    result = supervisor.supervisor_node(state)

    assert result["next_action"] == "teach"
    assert result["target_topic"] == "Equivalent fractions"
    assert "Rejected an ineligible revise_prerequisite target" in result["supervisor_reasoning"]


def test_supervisor_node_accepts_eligible_revise_prerequisite_target(monkeypatch):
    monkeypatch.setattr(
        supervisor,
        "call_groq_with_retry",
        lambda *a, **k: {
            "next_action": "revise_prerequisite",
            "target_topic": "Fractions as equal parts",
            "reasoning": "low mastery on the prerequisite",
        },
    )
    state = {
        "mode": "teaching",
        "subject": "math",
        "topic": "Equivalent fractions",
        "student_memory": {"mastery": {"fractions as equal parts": 0.2}},
    }
    result = supervisor.supervisor_node(state)

    assert result["next_action"] == "revise_prerequisite"
    assert result["target_topic"] == "Fractions as equal parts"


# ---------------------------------------------------------------------------
# route_from_supervisor
# ---------------------------------------------------------------------------


def test_route_from_supervisor_complete():
    assert supervisor.route_from_supervisor({"next_action": "complete"}) == "complete"


@pytest.mark.parametrize("action", ["teach", "revise_prerequisite"])
def test_route_from_supervisor_subject_agent(action):
    state = {"next_action": action, "subject": "science"}
    assert supervisor.route_from_supervisor(state) == "science_agent"


def test_route_from_supervisor_document_tutor_takes_priority_over_subject():
    state = {"next_action": "teach", "subject": "math", "document_id": "doc-1"}
    assert supervisor.route_from_supervisor(state) == "document_tutor"


def test_route_from_supervisor_quiz_and_feedback():
    assert supervisor.route_from_supervisor({"next_action": "quiz"}) == "quiz_generator"
    assert supervisor.route_from_supervisor({"next_action": "feedback"}) == "feedback_agent"


def test_route_from_supervisor_unsupported_subject_raises():
    with pytest.raises(ValueError):
        supervisor.route_from_supervisor({"next_action": "teach", "subject": "history"})


def test_route_from_supervisor_unsupported_action_raises():
    with pytest.raises(ValueError):
        supervisor.route_from_supervisor({"next_action": "do_a_backflip"})
