from __future__ import annotations

from types import SimpleNamespace

import pytest

from agents import tools


# ---------------------------------------------------------------------------
# python_calculator - restricted AST evaluator (Phase 1C)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("(3/4) + (1/8)", 0.875),
        ("2 ** 10", 1024),
        ("7 // 2", 3),
        ("7 % 2", 1),
        ("-5 + 2", -3),
        ("sqrt(144)", 12.0),
        ("abs(-9)", 9),
        ("round(3.14159, 2)", 3.14),
        ("min(4, 2, 9)", 2),
        ("max(4, 2, 9)", 9),
    ],
)
def test_python_calculator_evaluates_whitelisted_expressions(expression, expected):
    result = tools.python_calculator(expression)
    assert "error" not in result
    assert result["result"] == pytest.approx(expected)


def test_python_calculator_rejects_empty_expression():
    result = tools.python_calculator("")
    assert result == {"expression": "", "error": "Empty expression."}


def test_python_calculator_reports_division_by_zero():
    result = tools.python_calculator("1/0")
    assert result["error"] == "Division by zero."


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo hi')",
        "().__class__",
        "open('secrets.txt')",
        "[x for x in range(3)]",
        "1; 2",
        "os.system('echo hi')",
    ],
)
def test_python_calculator_rejects_unsafe_expressions(expression):
    result = tools.python_calculator(expression)
    assert "result" not in result
    assert "error" in result


# ---------------------------------------------------------------------------
# get_prerequisites - thin wrapper over api.prerequisites
# ---------------------------------------------------------------------------


def test_get_prerequisites_known_topic():
    result = tools.get_prerequisites("math", "equivalent fractions")
    assert result["found"] is True
    assert "fractions as equal parts" in result["prerequisites"]


def test_get_prerequisites_unknown_topic():
    result = tools.get_prerequisites("math", "quantum mechanics")
    assert result == {"topic": "quantum mechanics", "prerequisites": [], "found": False}


# ---------------------------------------------------------------------------
# search_ncert - falls back to an unfiltered subject/grade search when a
# chapter-scoped search comes up empty (Phase 1C/4B behavior).
# ---------------------------------------------------------------------------


def test_search_ncert_returns_empty_for_blank_query(monkeypatch):
    calls = []
    monkeypatch.setattr(tools, "retrieve", lambda *a, **k: calls.append((a, k)) or [])
    assert tools.search_ncert("math", 6, "   ") == []
    assert calls == []


def test_search_ncert_falls_back_when_chapter_scoped_search_is_empty(monkeypatch):
    calls = []

    def fake_retrieve(query, subject, grade, chapter=None, top_k=5):
        calls.append(chapter)
        if chapter:
            return []
        return [{"text": "fallback chunk", "chapter_title": "Fractions", "chapter_num": "5", "page_start": 1, "score": 0.1}]

    monkeypatch.setattr(tools, "retrieve", fake_retrieve)
    results = tools.search_ncert("math", 6, "fractions", chapter="Nonexistent Chapter")

    assert calls == ["Nonexistent Chapter", None]
    assert len(results) == 1
    assert results[0]["text"] == "fallback chunk"


def test_search_ncert_does_not_fall_back_when_no_chapter_was_requested(monkeypatch):
    calls = []
    monkeypatch.setattr(tools, "retrieve", lambda *a, **k: calls.append(k.get("chapter")) or [])
    results = tools.search_ncert("math", 6, "fractions")
    assert results == []
    assert calls == [None]


# ---------------------------------------------------------------------------
# execute_tool_call - the model-facing dispatcher. Must never raise: a bad
# tool call should degrade into a tool-result the model can react to.
# ---------------------------------------------------------------------------


def _fake_tool_call(name: str, arguments: str) -> SimpleNamespace:
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=arguments))


def test_execute_tool_call_python_calculator():
    tool_call = _fake_tool_call("python_calculator", '{"expression": "2 + 2"}')
    result, chunks = tools.execute_tool_call(tool_call, subject="math", grade=6, chapter="")
    assert result["result"] == 4
    assert chunks == []


def test_execute_tool_call_get_prerequisites():
    tool_call = _fake_tool_call("get_prerequisites", '{"topic": "equivalent fractions"}')
    result, chunks = tools.execute_tool_call(tool_call, subject="math", grade=6, chapter="")
    assert result["found"] is True
    assert chunks == []


def test_execute_tool_call_search_ncert_returns_chunks(monkeypatch):
    chunk = {"text": "chunk", "chapter_title": "Fractions", "chapter_num": "5", "page_start": 1, "score": 0.1}
    monkeypatch.setattr(tools, "retrieve", lambda *a, **k: [chunk])

    tool_call = _fake_tool_call("search_ncert", '{"query": "fractions"}')
    result, chunks = tools.execute_tool_call(tool_call, subject="math", grade=6, chapter="Fractions")

    assert result == {"chunks": [chunk]}
    assert chunks == [chunk]


def test_execute_tool_call_search_ncert_notes_empty_result(monkeypatch):
    monkeypatch.setattr(tools, "retrieve", lambda *a, **k: [])

    tool_call = _fake_tool_call("search_ncert", '{"query": "fractions"}')
    result, chunks = tools.execute_tool_call(tool_call, subject="math", grade=6, chapter="")

    assert result["chunks"] == []
    assert "note" in result
    assert chunks == []


def test_execute_tool_call_unknown_tool_name():
    tool_call = _fake_tool_call("delete_database", "{}")
    result, chunks = tools.execute_tool_call(tool_call, subject="math", grade=6, chapter="")
    assert "error" in result
    assert chunks == []


def test_execute_tool_call_malformed_json_arguments_defaults_to_empty():
    tool_call = _fake_tool_call("python_calculator", "not json")
    result, chunks = tools.execute_tool_call(tool_call, subject="math", grade=6, chapter="")
    # Falls back to `{}`, so python_calculator sees expression="" -> its own
    # empty-expression guard, not a crash.
    assert result == {"expression": "", "error": "Empty expression."}
    assert chunks == []


def test_execute_tool_call_reports_tool_exception_without_raising(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("embedding API timed out")

    monkeypatch.setattr(tools, "search_ncert", boom)
    tool_call = _fake_tool_call("search_ncert", '{"query": "fractions"}')
    result, chunks = tools.execute_tool_call(tool_call, subject="math", grade=6, chapter="")

    assert "error" in result
    assert "embedding API timed out" in result["error"]
    assert chunks == []
