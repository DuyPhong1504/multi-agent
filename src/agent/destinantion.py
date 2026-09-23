from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import call_llm, parse_json
from agent.places import NominatimPlacesProvider, PlacesProvider
from graph.state import Place, TripRequirements


logger = logging.getLogger(__name__)


DESTINATION_SYSTEM_PROMPT = """You are a travel destination research agent.
Return ONLY valid JSON with this exact schema:
{
  "places": [
	  {
	    "id": "string",
	    "name": "string",
	    "category": "string",
	    "address": "string"
	  }
  ]
}

Rules:
- Recommend destination areas or places relevant to the trip requirements.
- Return only the candidate name, category, and address.
- Do not include latitude, longitude, opening hours, prices, or URLs.
- Return an empty list when no suitable place can be identified.
"""


def parse_destination_candidates(content: str | dict[str, Any]) -> list[dict[str, str]]:
	"""Parse the LLM output without accepting tool-owned place fields."""
	payload = parse_json(content)
	if not isinstance(payload, dict) or not isinstance(payload.get("places"), list):
		raise ValueError("Destination response must contain a 'places' list")

	candidates = []
	for place in payload["places"]:
		if not isinstance(place, dict):
			raise ValueError("Each destination candidate must be a JSON object")
		candidate = {
			field: place.get(field, "")
			for field in ("id", "name", "category", "address")
		}
		if not all(candidate.values()):
			raise ValueError("Each destination candidate needs id, name, category, and address")
		candidates.append(candidate)

	return candidates


def destination_node(
	state: dict[str, Any],
	places_provider: PlacesProvider | None = None,
) -> dict[str, Any]:
	"""LangGraph node that finds candidate destinations for the requirements."""
	logger.info("[destination] START: searching candidate destinations")
	requirements = state.get("requirements")
	if not isinstance(requirements, TripRequirements):
		logger.error("[destination] FAILED: trip requirements are missing")
		return {"error": "Trip requirements are required before destination search"}

	prompt = (
		"Find suitable destinations for these requirements.\n"
		f"{requirements.to_dict()}"
	)

	try:
		logger.info(
			"[destination] Calling LLM for destination=%s",
			requirements.destination,
		)
		response = call_llm(
			[
				SystemMessage(content=DESTINATION_SYSTEM_PROMPT),
				HumanMessage(content=prompt),
			]
		)
		candidates = parse_destination_candidates(response.content)
		provider = places_provider or NominatimPlacesProvider()
		places = []
		for candidate in candidates:
			place = provider.enrich(candidate, requirements.destination)
			if place is not None:
				places.append(place)
			else:
				logger.warning(
					"[destination] Could not resolve candidate: %s",
					candidate["name"],
				)
		logger.info(
				"[destination] Enriched %d/%d candidates from Places provider",
				len(places),
				len(candidates),
			)
		if candidates and not places:
			return {
				"error": "Places provider could not resolve any destination candidates"
			}
	except (RuntimeError, ValueError) as exc:
		logger.error("[destination] FAILED: %s", exc)
		return {"error": str(exc)}
	except Exception as exc:
		logger.exception("[destination] FAILED: unexpected destination search error")
		return {"error": f"Destination search failed: {exc}"}

	logger.info("[destination] SUCCESS: found %d places", len(places))
	return {"destinations": places, "places": places, "error": None}
