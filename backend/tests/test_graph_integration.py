"""Phase 5: integration test for the full Supervisor -> Learning Agent ->
Reflection -> Supervisor loop (agents/graph.py:run_session), and the
Supervisor -> quiz_generator -> Supervisor loop. Every Groq call in the path
is mocked at the module boundary each agent already imports
`call_groq_with_retry`/`_create_completion` through - this exercises the real
graph wiring (agents/graph.py) and the real routing/guardrail logic (Phase
1A/1D), not a re-mock of those unit tests.
"""
from __future__ import annotations

from types import SimpleNamespace

from agents import graph, quiz_agent, reflection, subject_agents, supervisor, tools


def _tool_call_message(name: str, arguments: str) -> SimpleNamespace:
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name=name, arguments=arguments),
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=[tool_call]))]
    )


def _final_answer_message(payload: dict) -> SimpleNamespace:
    import json

    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload), tool_calls=None))]
    )


def test_full_teach_and_reflect_loop_reaches_complete(monkeypatch):
    # Supervisor's only LLM decision this turn: teach the requested topic.
    monkeypatch.setattr(
        supervisor,
        "call_groq_with_retry",
        lambda *a, **k: {"next_action": "teach", "target_topic": "", "reasoning": "student is ready"},
    )

    # math_agent's tool-calling loop: one search_ncert call, then a final
    # JSON answer with no further tool calls.
    teaching_payload = {
        "headline": "Equivalent Fractions",
        "explanation": "Two fractions are equivalent when they represent the same value.",
        "ncert_example": "1/2 = 2/4",
        "analogy": "Same pizza, cut into different numbers of equal slices.",
        "common_mistake": "Assuming only the numerator needs to match.",
        "guiding_question": "What happens if you multiply both parts by the same number?",
        "topics_covered": ["equivalent fractions"],
    }
    responses = iter(
        [
            _tool_call_message("search_ncert", '{"query": "equivalent fractions"}'),
            _final_answer_message(teaching_payload),
        ]
    )
    monkeypatch.setattr(subject_agents, "_create_completion", lambda *a, **k: next(responses))

    chunk = {"text": "Equivalent fractions represent the same value.", "chapter_title": "Fractions", "chapter_num": "5", "page_start": 12, "score": 0.05}
    monkeypatch.setattr(tools, "retrieve", lambda *a, **k: [chunk])

    # Reflection Agent passes the output outright - retry/force-accept
    # mechanics are already covered by test_reflection.py.
    monkeypatch.setattr(reflection, "call_groq_with_retry", lambda *a, **k: {"passed": True})

    initial_state = {
        "session_id": "sess-1",
        "student_id": "student-1",
        "grade": 6,
        "subject": "math",
        "chapter": "Fractions",
        "topic": "Equivalent fractions",
        "mode": "teaching",
        "retrieved_context": [],
        "teaching_output": {},
        "quiz_questions": [],
        "current_question_index": 0,
        "student_answer": "",
        "feedback_output": {},
        "session_score": 0.0,
        "weak_topics": [],
        "messages": [],
        "student_memory": {},
    }

    final_state = graph.run_session(initial_state)

    assert final_state["next_action"] == "complete"
    assert final_state["teaching_agent"] == "math_agent"
    assert final_state["teaching_output"]["headline"] == "Equivalent Fractions"
    assert final_state["retrieved_context"], "grounding guarantee: a real search_ncert chunk must be recorded"
    assert final_state["teaching_reflection"] == {}


def test_full_quiz_loop_reaches_complete(monkeypatch):
    monkeypatch.setattr(
        supervisor,
        "call_groq_with_retry",
        lambda *a, **k: {"next_action": "quiz", "target_topic": "", "reasoning": "topic teaching is done"},
    )

    quiz_payload = {
        "questions": [
            {
                "question": "What is 1/2 + 1/4?",
                "options": ["1/6", "2/6", "3/4", "1/4"],
                "correct_answer": "3/4",
                "explanation": "Convert to quarters: 2/4 + 1/4 = 3/4.",
                "concept_tested": "fraction addition",
            },
            {
                "question": "Is 2/4 equivalent to 1/2?",
                "options": ["Yes", "No"],
                "correct_answer": "Yes",
                "explanation": "Both represent half of a whole.",
                "concept_tested": "equivalent fractions",
            },
            {
                "question": "Which fraction is largest?",
                "options": ["1/3", "1/2", "1/4"],
                "correct_answer": "1/2",
                "explanation": "A smaller denominator means larger parts.",
                "concept_tested": "comparing fractions",
            },
        ]
    }
    monkeypatch.setattr(quiz_agent, "call_groq_with_retry", lambda *a, **k: quiz_payload)
    monkeypatch.setattr(quiz_agent, "_get_context", lambda state: [])

    initial_state = {
        "session_id": "sess-2",
        "student_id": "student-1",
        "grade": 6,
        "subject": "math",
        "chapter": "Fractions",
        "topic": "Equivalent fractions",
        "mode": "quiz",
        "retrieved_context": [],
        "teaching_output": {"headline": "Equivalent Fractions"},
        "quiz_questions": [],
        "current_question_index": 0,
        "student_answer": "",
        "feedback_output": {},
        "session_score": 0.0,
        "weak_topics": [],
        "messages": [],
        "student_memory": {},
    }

    final_state = graph.run_session(initial_state)

    assert final_state["next_action"] == "complete"
    assert len(final_state["quiz_questions"]) == 3
    assert final_state["current_question_index"] == 0
