from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()


def build_llm() -> ChatOpenAI:
    """Build the shared OpenAI-compatible chat client without embedding secrets."""
    api_key = os.getenv("REQUIREMENT_API_KEY") or os.getenv("XAH_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing REQUIREMENT_API_KEY (or XAH_API_KEY) environment variable"
        )

    return ChatOpenAI(
        base_url=os.getenv("REQUIREMENT_BASE_URL", "https://api.xah.io/v1"),
        api_key=api_key,
        model=os.getenv("REQUIREMENT_MODEL", "gpt-5.6-luna"),
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def parse_json(content: str | dict[str, Any]) -> dict[str, Any]:
    """Parse an LLM response and require a JSON object."""
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

    if not isinstance(content, dict):
        raise ValueError("LLM response must be a JSON object")
    return content


def call_llm(messages: list[Any]) -> Any:
    """Call the shared LLM client used by every agent."""
    return build_llm().invoke(messages)