from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from agent.llm import call_llm, parse_json
from graph.state import TripRequirements


logger = logging.getLogger(__name__)


REQUIREMENT_SYSTEM_PROMPT = """You are a travel requirement extraction agent.
Extract trip requirements from the user's message and return ONLY valid JSON.
Do not return markdown, code fences, comments, or any explanation.

The JSON must match this exact schema:
{
  "destination": "string or null",
  "start_date": "YYYY-MM-DD string or null",
  "end_date": "YYYY-MM-DD string or null",
  "duration_days": 0,
  "travelers": 1,
  "budget": 0.0,
  "currency": "USD",
  "interests": [],
  "food_preferences": [],
  "transport_preference": "string or null",
  "accommodation_preference": "string or null",
  "avoid": [],
  "must_visit": [],
  "shopping_preferences": []
}

Rules:
- Preserve explicitly provided values.
- Use today's date from the runtime context when inferring a missing year.
- Convert dates written as DD/MM or DD-MM to YYYY-MM-DD. For example, if today
    is 2026-09-22, "28/10 đến 1/11" means "2026-10-28" to "2026-11-01".
- Use null when a string or budget is unknown, but do not use null for a date
    whose day and month are explicitly present in the user message.
- Use 0 for unknown duration_days.
- Use 1 for unknown travelers.
- Use USD when the currency is not specified.
- Every list must contain strings and must be [] when unknown.
- Do not invent dates, budget, destination, or preferences.
"""


DATE_RANGE_PATTERN = re.compile(
    r"(?P<start_day>\d{1,2})\s*[/.-]\s*(?P<start_month>\d{1,2})"
    r"(?:\s*(?:đến|tới|to|-|–|->)\s*)"
    r"(?P<end_day>\d{1,2})\s*[/.-]\s*(?P<end_month>\d{1,2})"
    r"(?:\s*[/.-]\s*(?P<end_year>\d{4}))?",
    re.IGNORECASE,
)


def _infer_date_range_from_message(
    content: str,
    today: date | None = None,
) -> tuple[str, str] | None:
    """Recover a DD/MM date range when the LLM omits an explicit year."""
    match = DATE_RANGE_PATTERN.search(content)
    if not match:
        return None

    today = today or date.today()
    start_day = int(match.group("start_day"))
    start_month = int(match.group("start_month"))
    end_day = int(match.group("end_day"))
    end_month = int(match.group("end_month"))
    end_year = int(match.group("end_year")) if match.group("end_year") else None
    start_year = today.year

    if end_year is None and (end_month, end_day) < (start_month, start_day):
        end_year = start_year + 1
    end_year = end_year or start_year

    try:
        start = date(start_year, start_month, start_day)
        end = date(end_year, end_month, end_day)
    except ValueError as exc:
        raise ValueError(f"Invalid date range in user message: {exc}") from exc

    return start.isoformat(), end.isoformat()


def _apply_date_fallback(
    requirements: TripRequirements,
    messages: list[BaseMessage],
) -> TripRequirements:
    """Fill only missing dates from the user's explicit numeric date range."""
    user_text = "\n".join(
        str(message.content)
        for message in messages
        if isinstance(message, HumanMessage)
    )
    inferred = _infer_date_range_from_message(user_text)
    if not inferred or (requirements.start_date and requirements.end_date):
        return requirements

    requirements.start_date, requirements.end_date = inferred
    return requirements


def parse_requirements_json(content: str | dict[str, Any]) -> TripRequirements:
    """Parse and validate the model response as TripRequirements."""
    data = parse_json(content)

    required = {
        "duration_days",
        "travelers",
        "currency",
        "interests",
        "food_preferences",
        "avoid",
        "must_visit",
        "shopping_preferences",
    }
    missing = required - data.keys()
    if missing:
        raise ValueError(f"LLM JSON missing required fields: {sorted(missing)}")

    for field in (
        "interests",
        "food_preferences",
        "avoid",
        "must_visit",
        "shopping_preferences",
    ):
        if not isinstance(data[field], list) or not all(
            isinstance(item, str) for item in data[field]
        ):
            raise ValueError(f"'{field}' must be a list of strings")

    try:
        return TripRequirements.from_dict(data)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid TripRequirements values: {exc}") from exc


def requirement_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph node that extracts structured trip requirements from messages."""
    messages: list[BaseMessage] = state.get("messages", [])
    logger.info("[requirements] START: extracting trip requirements")
    if not messages:
        logger.warning("[requirements] FAILED: no user message was provided")
        return {"error": "No user message was provided"}

    prompt_messages = [
        SystemMessage(
            content=(
                f"Runtime date: {date.today().isoformat()}\n\n"
                f"{REQUIREMENT_SYSTEM_PROMPT}"
            )
        ),
        *messages,
    ]

    try:
        logger.info("[requirements] Calling LLM")
        response = call_llm(prompt_messages)
        requirements = parse_requirements_json(response.content)
        requirements = _apply_date_fallback(requirements, messages)
    except (RuntimeError, ValueError) as exc:
        logger.error("[requirements] FAILED: %s", exc)
        return {
            "error": str(exc),
            "messages": prompt_messages,
        }
    except Exception as exc:
        logger.exception("[requirements] FAILED: unexpected LLM error")
        return {
            "error": f"Requirement LLM call failed: {exc}",
            "messages": prompt_messages,
        }

    logger.info(
        "[requirements] SUCCESS: destination=%s, duration_days=%s, budget=%s",
        requirements.destination,
        requirements.duration_days,
        requirements.budget,
    )
    return {
        "requirements": requirements,
        "messages": prompt_messages + [response],
        "error": None,
    }


def extract_requirements(user_input: str) -> TripRequirements:
    """Convenience wrapper for calling the requirement node directly."""
    result = requirement_node({"messages": [HumanMessage(content=user_input)]})
    if result.get("error"):
        raise ValueError(result["error"])
    return result["requirements"]