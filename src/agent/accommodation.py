from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import build_llm, parse_json
from graph.state import Accommodation, TripRequirements


logger = logging.getLogger(__name__)


ACCOMMODATION_SYSTEM_PROMPT = """You are a travel accommodation research agent.
Given the trip requirements and the candidate destinations, propose suitable
accommodation options for the trip.

Return ONLY valid JSON with this exact schema:
{
  "accommodations": [
    {
      "id": "string",
      "name": "string",
      "address": "string",
      "latitude": 0.0,
      "longitude": 0.0,
      "check_in": "YYYY-MM-DD",
      "check_out": "YYYY-MM-DD",
      "price_per_night": 0.0,
      "total_price": 0.0,
      "currency": "USD",
      "rating": 0.0,
      "url": "string or null"
    }
  ]
}

Rules:
- Prefer the user's accommodation_preference when choosing a type.
- check_in and check_out should match the trip dates when available.
- total_price should equal price_per_night * number of nights.
- price_per_night and total_price must be non-negative.
- rating must be between 0 and 5.
- Do not invent latitude/longitude unless you are confident; use 0.0 when unknown.
- Return an empty list when no suitable accommodation can be proposed.
"""


def _parse_accommodations(content: str | dict[str, Any]) -> list[Accommodation]:
    """Parse the LLM accommodation response into validated objects."""
    data = parse_json(content)
    if not isinstance(data, dict) or not isinstance(data.get("accommodations"), list):
        raise ValueError("Accommodation response must contain an 'accommodations' list")

    items: list[Accommodation] = []
    for item in data["accommodations"]:
        if not isinstance(item, dict):
            raise ValueError("Each accommodation item must be a JSON object")
        items.append(Accommodation.model_validate(item))
    return items


def accommodation_node(
    state: dict[str, Any],
    llm_factory: Any = build_llm,
) -> dict[str, Any]:
    """LangGraph node that proposes accommodation options for the trip."""
    logger.info("[accommodation] START: proposing accommodation")
    requirements = state.get("requirements")

    if not isinstance(requirements, TripRequirements):
        logger.error("[accommodation] FAILED: trip requirements are missing")
        return {"error": "Trip requirements are required before accommodation search"}

    prompt = (
        "Propose accommodation options for this trip.\n\n"
        f"Requirements:\n{requirements.model_dump_json()}"
    )

    try:
        response = llm_factory().invoke(
            [
                SystemMessage(content=ACCOMMODATION_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        accommodations = _parse_accommodations(response.content)
        logger.info("[accommodation] SUCCESS: %d options proposed", len(accommodations))
    except (RuntimeError, ValueError) as exc:
        logger.error("[accommodation] FAILED: %s", exc)
        return {"error": str(exc)}
    except Exception as exc:
        logger.exception("[accommodation] FAILED: unexpected LLM error")
        return {"error": f"Accommodation LLM call failed: {exc}"}

    return {"accommodations": accommodations, "error": None}