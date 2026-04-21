from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .orchestrator import ORCHESTRATOR_ROUTES, orchestrator_node, route_from_orchestrator
from .quiz_agent import feedback_agent, quiz_generator
from .state import LearningState
from .subject_agents import math_agent, science_agent, sst_agent

graph = StateGraph(LearningState)

graph.add_node("orchestrator", orchestrator_node)
graph.add_node("math_agent", math_agent)
graph.add_node("science_agent", science_agent)
graph.add_node("sst_agent", sst_agent)
graph.add_node("quiz_generator", quiz_generator)
graph.add_node("feedback_agent", feedback_agent)

graph.add_edge(START, "orchestrator")
graph.add_conditional_edges(
    "orchestrator",
    route_from_orchestrator,
    {**ORCHESTRATOR_ROUTES, "complete": END},
)
graph.add_edge("math_agent", "orchestrator")
graph.add_edge("science_agent", "orchestrator")
graph.add_edge("sst_agent", "orchestrator")
graph.add_edge("quiz_generator", "orchestrator")
graph.add_edge("feedback_agent", "orchestrator")

app = graph.compile()


def run_session(initial_state: dict) -> LearningState:
    return app.invoke(initial_state)
