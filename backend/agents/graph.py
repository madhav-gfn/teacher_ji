from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .document_agent import document_tutor
from .quiz_agent import feedback_agent, quiz_generator
from .reflection import reflection_agent, route_from_reflection
from .state import LearningState
from .subject_agents import math_agent, science_agent, sst_agent
from .supervisor import route_from_supervisor, supervisor_node

graph = StateGraph(LearningState)

graph.add_node("supervisor", supervisor_node)
graph.add_node("math_agent", math_agent)
graph.add_node("science_agent", science_agent)
graph.add_node("sst_agent", sst_agent)
graph.add_node("document_tutor", document_tutor)
graph.add_node("quiz_generator", quiz_generator)
graph.add_node("feedback_agent", feedback_agent)
graph.add_node("reflection_agent", reflection_agent)

graph.add_edge(START, "supervisor")
graph.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "math_agent": "math_agent",
        "science_agent": "science_agent",
        "sst_agent": "sst_agent",
        "document_tutor": "document_tutor",
        "quiz_generator": "quiz_generator",
        "feedback_agent": "feedback_agent",
        "complete": END,
    },
)
# Subject agents (math/science/sst) go through the Reflection Agent before the
# Supervisor sees their output - it can bounce a failing explanation back for
# one bounded retry. document_tutor/quiz_generator/feedback_agent skip
# reflection entirely (teaching-output-only gate, per master_plan.md 1D).
graph.add_edge("math_agent", "reflection_agent")
graph.add_edge("science_agent", "reflection_agent")
graph.add_edge("sst_agent", "reflection_agent")
graph.add_conditional_edges(
    "reflection_agent",
    route_from_reflection,
    {
        "math_agent": "math_agent",
        "science_agent": "science_agent",
        "sst_agent": "sst_agent",
        "supervisor": "supervisor",
    },
)
graph.add_edge("document_tutor", "supervisor")
graph.add_edge("quiz_generator", "supervisor")
graph.add_edge("feedback_agent", "supervisor")

app = graph.compile()


def run_session(initial_state: dict) -> LearningState:
    return app.invoke(initial_state)
