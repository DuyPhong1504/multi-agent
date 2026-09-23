from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import build_llm, parse_json
from graph.state import Activity, TripRequirements


logger = logging.getLogger(__name__)


ACTIVITY_SYSTEM_PROMPT = """You are a travel activity research agent.
Given a set of candidate destinations and the trip requirements, propose
concrete activities to fill each day of the trip.

Return ONLY valid JSON with this exact schema:
{
  "activities": [
    {
      "id": "string",
      "place_id": "string",
      "day": 1,
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "title": "string",
      "description": "string",
      "cost": 0.0,
      "currency": "USD"
    }
  ]
}

Rules:
- Only reference place_id values that were provided in the candidate list.
- Assign each activity to a concrete day (1-based) within the trip duration.
- Keep start_time and end_time as HH:MM strings.
- cost must be a non-negative number; use 0 when unknown.
- Do not invent latitude, longitude, opening hours, or URLs.
- Return an empty list when no suitable activity can be proposed.
"""


def _parse_activities(content: str | dict[str, Any]) -> list[Activity]:
	"""Parse the LLM activity response into validated Activity objects."""
	data = parse_json(content)
	if not isinstance(data, dict) or not isinstance(data.get("activities"), list):
		raise ValueError("Activity response must contain an 'activities' list")

	activities: list[Activity] = []
	for item in data["activities"]:
		if not isinstance(item, dict):
			raise ValueError("Each activity must be a JSON object")
		activity = Activity.model_validate(item)
		activities.append(activity)
	return activities


def activity_node(
	state: dict[str, Any],
	llm_factory: Any = build_llm,
) -> dict[str, Any]:
	"""LangGraph node that proposes candidate activities for the trip."""
	logger.info("[activity] START: proposing activities")
	requirements = state.get("requirements")
	destinations = state.get("destinations") or state.get("places") or []

	if not isinstance(requirements, TripRequirements):
		logger.error("[activity] FAILED: trip requirements are missing")
		return {"error": "Trip requirements are required before activity search"}
	if not destinations:
		logger.warning("[activity] No destinations available; returning empty set")

	place_snapshot = [
		{"id": place.id, "name": place.name, "category": place.category}
		for place in destinations
	]
	prompt = (
		"Propose a full itinerary of activities for this trip.\n\n"
		f"Requirements:\n{requirements.model_dump_json()}\n\n"
		f"Available candidate places:\n{place_snapshot}"
	)

	try:
		response = llm_factory().invoke(
			[
				SystemMessage(content=ACTIVITY_SYSTEM_PROMPT),
				HumanMessage(content=prompt),
			]
		)
		parsed = _parse_activities(response.content)
		# Keep only activities that reference a known place.
		known_ids = {place.id for place in destinations}
		activities = [
			activity
			for activity in parsed
			if activity.place_id in known_ids
		]
		logger.info(
			"[activity] SUCCESS: %d/%d activities reference known places",
			len(activities),
			len(parsed),
		)
	except (RuntimeError, ValueError) as exc:
		logger.error("[activity] FAILED: %s", exc)
		return {"error": str(exc)}
	except Exception as exc:
		logger.exception("[activity] FAILED: unexpected LLM error")
		return {"error": f"Activity LLM call failed: {exc}"}

	return {"activities": activities, "error": None}
