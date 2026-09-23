from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import build_llm, parse_json
from graph.state import Place, Transportation, TripRequirements


logger = logging.getLogger(__name__)


TRANSPORTATION_SYSTEM_PROMPT = """You are a travel transportation planning agent.
Given the trip requirements, the candidate places, and the proposed activities,
plan the transportation legs needed to move between places.

Return ONLY valid JSON with this exact schema:
{
  "transportation": [
    {
      "id": "string",
      "from_place_id": "string",
      "to_place_id": "string",
      "mode": "string",
      "departure_time": "HH:MM or null",
      "arrival_time": "HH:MM or null",
      "duration_minutes": 0,
      "distance_km": 0.0,
      "cost": 0.0,
      "currency": "USD"
    }
  ]
}

Rules:
- Only reference place_id values that were provided in the candidate list.
- mode should be one of: flight, train, metro, bus, taxi, walking.
- Prefer the user's transport_preference when choosing a mode.
- duration_minutes and distance_km are estimates; keep them non-negative.
- cost must be a non-negative number; use 0 when unknown.
- Do not invent latitude, longitude, opening hours, or URLs.
- Return an empty list when no transportation is needed.
"""


def _parse_transportation(content: str | dict[str, Any]) -> list[Transportation]:
    """Parse the LLM transportation response into validated objects."""
    data = parse_json(content)
    if not isinstance(data, dict) or not isinstance(data.get("transportation"), list):
        raise ValueError("Transportation response must contain a 'transportation' list")

    items: list[Transportation] = []
    for item in data["transportation"]:
        if not isinstance(item, dict):
            raise ValueError("Each transportation item must be a JSON object")
        items.append(Transportation.model_validate(item))
    return items


def transportation_node(
    state: dict[str, Any],
    llm_factory: Any = build_llm,
) -> dict[str, Any]:
    """LangGraph node that plans transportation between candidate places."""
    logger.info("[transportation] START: planning transportation")
    requirements = state.get("requirements")
    places = state.get("places") or state.get("destinations") or []

    if not isinstance(requirements, TripRequirements):
        logger.error("[transportation] FAILED: trip requirements are missing")
        return {"error": "Trip requirements are required before transportation planning"}
    if not places:
        logger.warning("[transportation] No places available; returning empty set")

    place_snapshot = [
        {"id": place.id, "name": place.name, "category": place.category}
        for place in places
    ]
    prompt = (
        "Plan the transportation legs for this trip.\n\n"
        f"Requirements:\n{requirements.model_dump_json()}\n\n"
        f"Available candidate places:\n{place_snapshot}"
    )

    try:
        response = llm_factory().invoke(
            [
                SystemMessage(content=TRANSPORTATION_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        parsed = _parse_transportation(response.content)
        # Keep only legs that reference known places.
        known_ids = {place.id for place in places}
        transportation = [
            item
            for item in parsed
            if item.from_place_id in known_ids and item.to_place_id in known_ids
        ]
        logger.info(
            "[transportation] SUCCESS: %d/%d legs reference known places",
            len(transportation),
            len(parsed),
        )
    except (RuntimeError, ValueError) as exc:
        logger.error("[transportation] FAILED: %s", exc)
        return {"error": str(exc)}
    except Exception as exc:
        logger.exception("[transportation] FAILED: unexpected LLM error")
        return {"error": f"Transportation LLM call failed: {exc}"}

    return {"transportation": transportation, "error": None}