from __future__ import annotations

import json
import logging
import os
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from graph.state import Place


logger = logging.getLogger(__name__)


class PlacesProvider(Protocol):
    """Provider contract for enriching LLM candidates with place data."""

    def enrich(
        self,
        candidate: dict[str, str],
        destination: str | None = None,
    ) -> Place | None:
        ...


class NominatimPlacesProvider:
    """Resolve candidates with OpenStreetMap's Nominatim search API."""

    def __init__(
        self,
        base_url: str | None = None,
        user_agent: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url or os.getenv(
            "PLACES_API_URL", "https://nominatim.openstreetmap.org/search"
        )
        self.user_agent = user_agent or os.getenv(
            "PLACES_USER_AGENT", "automated-travel-planner/0.1"
        )
        self.timeout = timeout

    def enrich(
        self,
        candidate: dict[str, str],
        destination: str | None = None,
    ) -> Place | None:
        queries = self._queries(candidate, destination)
        for query in queries:
            logger.info("[places] Searching: %s", query)
            try:
                result = self._search(query)
            except Exception:
                logger.exception("[places] Search failed: %s", query)
                continue
            if result is not None:
                return self._to_place(candidate, result)

        logger.warning("[places] No result for candidate: %s", candidate["name"])
        return None

    def _search(self, query: str) -> dict[str, Any] | None:
        params = urlencode(
            {
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "addressdetails": 1,
                "extratags": 1,
            }
        )
        request = Request(
            f"{self.base_url}?{params}",
            headers={"User-Agent": self.user_agent},
        )
        with urlopen(request, timeout=self.timeout) as response:
            results = json.load(response)
        if not isinstance(results, list) or not results:
            return None
        result = results[0]
        return result if isinstance(result, dict) else None

    @staticmethod
    def _queries(
        candidate: dict[str, str],
        destination: str | None,
    ) -> list[str]:
        name = candidate.get("name", "").strip()
        address = candidate.get("address", "").strip()
        queries = [
            ", ".join(value for value in (name, address) if value),
            ", ".join(value for value in (name, destination, "China") if value),
            name,
        ]
        return list(dict.fromkeys(query for query in queries if query))

    @staticmethod
    def _to_place(candidate: dict[str, str], result: dict[str, Any]) -> Place:
        extratags = result.get("extratags") or {}
        return Place(
            id=candidate["id"],
            name=candidate["name"],
            category=candidate["category"],
            address=result.get("display_name") or candidate.get("address", ""),
            latitude=float(result["lat"]),
            longitude=float(result["lon"]),
            opening_time=extratags.get("opening_hours"),
            url=extratags.get("website") or extratags.get("contact:website"),
        )