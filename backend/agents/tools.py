"""
Phase 1C: tools the Learning Agent (math_agent/science_agent/sst_agent) can
choose to call via Groq tool-calling, instead of the retrieval step running
unconditionally before every generation.

`TOOL_SPECS` is the OpenAI/Groq-compatible function-calling schema handed to
`chat.completions.create(tools=...)`. `execute_tool_call` dispatches a single
tool call returned by the model and always returns a JSON-serializable dict
(never raises) so a bad tool call degrades into a tool-result the model can
react to, rather than crashing the turn.
"""
from __future__ import annotations

import ast
import json
import math
import operator

from langsmith import traceable

from api.prerequisites import get_prerequisites as _lookup_prerequisites
from rag.retriever import retrieve

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "search_ncert",
            "description": (
                "Search the NCERT textbook for this student's subject and grade, "
                "returning the most relevant passages. Call this before writing an "
                "explanation so it can be grounded in real textbook content."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for - the topic plus any specific sub-concept.",
                    },
                    "chapter": {
                        "type": "string",
                        "description": (
                            "Optional. Restrict the search to this chapter. Omit to search "
                            "the whole subject/grade textbook if a chapter-scoped search "
                            "returns nothing useful."
                        ),
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_prerequisites",
            "description": (
                "Look up the foundational topics a concept depends on, from the "
                "curriculum dependency map. Use this when the student's profile shows "
                "low mastery, or flags this topic as weak_topic/revision_due, to decide "
                "whether a prerequisite needs a quick refresher first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The concept to look up prerequisites for.",
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "python_calculator",
            "description": (
                "Evaluate a numeric arithmetic expression exactly, to verify a computed "
                "answer before presenting it to the student. Supports +, -, *, /, //, %, "
                "**, parentheses, and abs/round/min/max/sqrt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A numeric expression, e.g. '(3/4) + (1/8)' or 'sqrt(144)'.",
                    },
                },
                "required": ["expression"],
            },
        },
    },
]


@traceable(run_type="tool", name="search_ncert")
def search_ncert(subject: str, grade: int, query: str, chapter: str | None = None, top_k: int = 5) -> list[dict]:
    query = (query or "").strip()
    if not query:
        return []
    chunks = retrieve(query, subject, grade, chapter or None, top_k=top_k)
    if chunks or not chapter:
        return chunks
    # Chapter-scoped search came up empty - broaden to the whole subject/grade index.
    return retrieve(query, subject, grade, chapter=None, top_k=top_k)


@traceable(run_type="tool", name="get_prerequisites")
def get_prerequisites(subject: str, topic: str) -> dict:
    return _lookup_prerequisites(subject, topic)


class _UnsafeExpression(ValueError):
    """Raised when an expression uses anything outside the calculator's whitelist."""


_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARYOPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
_ALLOWED_FUNCS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
}


def _eval_node(node: ast.AST):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise _UnsafeExpression("Only numeric constants are allowed.")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        return _ALLOWED_UNARYOPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Call):
        if node.keywords or not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCS:
            raise _UnsafeExpression("Only abs/round/min/max/sqrt calls with positional args are allowed.")
        return _ALLOWED_FUNCS[node.func.id](*(_eval_node(arg) for arg in node.args))
    raise _UnsafeExpression(f"Unsupported expression element: {type(node).__name__}")


@traceable(run_type="tool", name="python_calculator")
def python_calculator(expression: str) -> dict:
    expression = (expression or "").strip()
    if not expression:
        return {"expression": expression, "error": "Empty expression."}
    try:
        tree = ast.parse(expression, mode="eval")
        return {"expression": expression, "result": _eval_node(tree.body)}
    except ZeroDivisionError:
        return {"expression": expression, "error": "Division by zero."}
    except (_UnsafeExpression, SyntaxError, TypeError, ValueError) as exc:
        return {"expression": expression, "error": f"Invalid expression: {exc}"}


def execute_tool_call(tool_call, *, subject: str, grade: int, chapter: str) -> tuple[dict, list[dict]]:
    """Run one model-requested tool call. Returns (json_result, retrieved_chunks) -
    chunks is non-empty only for search_ncert, and feeds the caller's
    `retrieved_context` accumulator for citations/downstream quiz generation."""
    name = tool_call.function.name
    try:
        arguments = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        arguments = {}

    try:
        if name == "search_ncert":
            chunks = search_ncert(
                subject,
                grade,
                arguments.get("query", ""),
                arguments.get("chapter") or chapter or None,
            )
            if chunks:
                return {"chunks": chunks}, chunks
            return {"chunks": [], "note": "No matching NCERT content found for this query."}, []

        if name == "get_prerequisites":
            return get_prerequisites(subject, arguments.get("topic", "")), []

        if name == "python_calculator":
            return python_calculator(arguments.get("expression", "")), []

        return {"error": f"Unknown tool '{name}'."}, []
    except Exception as exc:
        # A tool's own execution can fail transiently - e.g. the embedding API
        # search_ncert depends on timing out or returning a 5xx. Report that
        # back to the model as a tool result it can react to (skip this
        # source, try a different query, or just answer without it) instead
        # of letting it crash the whole teaching turn.
        return {"error": f"Tool '{name}' failed: {exc}"}, []
