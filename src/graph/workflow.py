from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from agent.accommodation import accommodation_node
from agent.activity import activity_node
from agent.destinantion import destination_node
from agent.requirement import requirement_node
from agent.transportation import transportation_node
from graph.state import GraphState


logger = logging.getLogger(__name__)


NodeHandler = Callable[[dict[str, Any]], dict[str, Any]]


def build_requirement_graph(
	requirements_handler: NodeHandler = requirement_node,
	destination_handler: NodeHandler = destination_node,
	activity_handler: NodeHandler = activity_node,
	transportation_handler: NodeHandler = transportation_node,
	accommodation_handler: NodeHandler = accommodation_node,
):
	"""Build and compile the requirements-to-activities graph.

	The handlers are injectable so the workflow remains easy to test.
	"""
	graph = StateGraph(GraphState)
	graph.add_node("requirements", requirements_handler)
	graph.add_node("destination", destination_handler)
	graph.add_node("activity", activity_handler)
	graph.add_node("transportation", transportation_handler)
	graph.add_node("accommodation", accommodation_handler)
	graph.add_edge(START, "requirements")
	graph.add_edge("requirements", "destination")
	graph.add_edge("destination", "activity")
	graph.add_edge("activity", "transportation")
	graph.add_edge("transportation", "accommodation")
	graph.add_edge("accommodation", END)
	logger.info(
		"Workflow compiled: requirements -> destination -> activity -> transportation -> accommodation"
	)
	return graph.compile()


requirement_graph = build_requirement_graph()


def run_requirements(messages: list[Any]) -> dict[str, Any]:
	"""Run requirement extraction through the compiled LangGraph workflow."""
	logger.info("Workflow START")
	result = requirement_graph.invoke({"messages": messages})
	if result.get("error"):
		logger.error("Workflow FAILED: %s", result["error"])
	else:
		logger.info(
			"Workflow SUCCESS: %d destinations, %d activities",
			len(result.get("destinations", [])),
			len(result.get("activities", [])),
		)
	return result
