from __future__ import annotations

import json
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TripRequirements(BaseModel):
    model_config = ConfigDict(extra="ignore")

    destination: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    duration_days: int = Field(default=0, ge=0)
    travelers: int = Field(default=1, ge=1)

    budget: float | None = Field(default=None, ge=0)
    currency: str = "USD"

    interests: list[str] = Field(default_factory=list)
    food_preferences: list[str] = Field(default_factory=list)
    transport_preference: str | None = None

    accommodation_preference: str | None = None

    avoid: list[str] = Field(default_factory=list)
    must_visit: list[str] = Field(default_factory=list)
    shopping_preferences: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "TripRequirements":
        return cls.model_validate(data)


class Place(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    category: str
    address: str = ""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    price: float | None = Field(default=None, ge=0)
    currency: str | None = None
    opening_time: str | None = None
    closing_time: str | None = None
    url: str | None = None


class Activity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    place_id: str
    day: int = Field(ge=1)
    start_time: str
    end_time: str
    title: str
    description: str = ""
    cost: float = Field(default=0, ge=0)
    currency: str = "USD"


class Transportation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    from_place_id: str
    to_place_id: str
    mode: str
    departure_time: str | None = None
    arrival_time: str | None = None
    duration_minutes: int = Field(ge=0)
    distance_km: float = Field(ge=0)
    cost: float = Field(default=0, ge=0)
    currency: str = "USD"


class Route(BaseModel):
    model_config = ConfigDict(extra="ignore")

    from_place_id: str
    to_place_id: str
    mode: str
    duration_minutes: int = Field(ge=0)
    distance_km: float = Field(ge=0)
    geometry: dict[str, Any] = Field(default_factory=dict)


class Accommodation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    address: str = ""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    check_in: str
    check_out: str
    price_per_night: float = Field(ge=0)
    total_price: float = Field(ge=0)
    currency: str = "USD"
    rating: float | None = Field(default=None, ge=0, le=5)
    url: str | None = None


class Souvenir(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    category: str
    recipient: str
    price: float = Field(ge=0)
    currency: str = "USD"
    place_id: str
    day: int = Field(ge=1)
    priority: str


class BudgetItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: str
    description: str
    amount: float = Field(ge=0)
    currency: str = "USD"
    day: int | None = Field(default=None, ge=1)


class DayPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day: int = Field(ge=1)
    date: str
    activities: list[Activity] = Field(default_factory=list)
    transportation: list[Transportation] = Field(default_factory=list)
    estimated_cost: float = Field(default=0, ge=0)

    @field_validator("estimated_cost")
    @classmethod
    def validate_estimated_cost(cls, value: float) -> float:
        return round(value, 2)


class TripState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    requirements: TripRequirements
    destinations: list[Place] = Field(default_factory=list)
    places: list[Place] = Field(default_factory=list)
    activities: list[Activity] = Field(default_factory=list)
    transportation: list[Transportation] = Field(default_factory=list)
    accommodations: list[Accommodation] = Field(default_factory=list)
    routes: list[Route] = Field(default_factory=list)
    souvenirs: list[Souvenir] = Field(default_factory=list)
    budget_items: list[BudgetItem] = Field(default_factory=list)
    daily_plans: list[DayPlan] = Field(default_factory=list)
    total_cost: float = Field(default=0, ge=0)
    remaining_budget: float | None = None
    review_errors: list[str] = Field(default_factory=list)
    status: str = "draft"


class GraphState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    requirements: TripRequirements
    destinations: list[Place]
    places: list[Place]
    activities: list[Activity]
    transportation: list[Transportation]
    accommodations: list[Accommodation]
    trip: TripState
    error: str | None
    