from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


@dataclass
class Topic:
    title: str
    description: str
    estimated_time: int
    prerequisites: list[str] = field(default_factory=list)
    status: str = "pending"

    def to_dict(self) -> dict:
        """Convert to plain dict for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Topic":
        """Reconstruct from a plain dict (e.g., after JSON round-trip)."""
        return cls(
            title=data["title"],
            description=data["description"],
            estimated_time=data["estimated_time"],
            prerequisites=data.get("prerequisites", []),
            status=data.get("status", "pending"),
        )

@dataclass
class StudyRoadmap:
    goal: str
    total_weeks: int
    topics: list[Topic]
    weekly_hours: int = 5

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "goal": self.goal,
            "total_weeks": self.total_weeks,
            "weekly_hours": self.weekly_hours,
            "topics": [t.to_dict() for t in self.topics],
        }