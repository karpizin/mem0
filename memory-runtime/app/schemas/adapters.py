from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.event import ALLOWED_EVENT_ORIGINS, ALLOWED_SPACE_HINTS, EventMessage, EventRead
from app.schemas.recall import MemoryBrief, RecallTrace


class AdapterEventCreate(BaseModel):
    namespace_id: str
    agent_id: str | None = None
    session_id: str | None = None
    project_id: str | None = None
    event_type: str = Field(..., min_length=2, max_length=100)
    event_origin: str | None = None
    timestamp: datetime | None = None
    space_hint: str | None = None
    messages: list[EventMessage] = Field(..., min_length=1)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    dedupe_key: str | None = None

    @field_validator("space_hint")
    @classmethod
    def validate_space_hint(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in ALLOWED_SPACE_HINTS:
            raise ValueError(f"Unsupported space_hint '{value}'")
        return normalized

    @field_validator("event_origin")
    @classmethod
    def validate_event_origin(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if normalized not in ALLOWED_EVENT_ORIGINS:
            raise ValueError(f"Unsupported event_origin '{value}'")
        return normalized


class AdapterEventRead(BaseModel):
    adapter: str
    source_system: str
    event: EventRead


class AdapterRecallRequest(BaseModel):
    namespace_id: str
    agent_id: str | None = None
    session_id: str | None = None
    query: str = Field(..., min_length=3)
    context_budget_tokens: int = Field(..., gt=0)
    space_filter: list[str] | None = None


class AdapterRecallResponse(BaseModel):
    adapter: str
    source_system: str
    brief: MemoryBrief
    trace: RecallTrace


class AdapterBootstrapRequest(BaseModel):
    namespace_name: str = Field(..., min_length=3, max_length=255)
    agent_name: str = Field(default="primary", min_length=2, max_length=255)
    external_ref: str | None = Field(default=None, max_length=255)


class AdapterBootstrapResponse(BaseModel):
    adapter: str
    source_system: str
    namespace_id: str
    namespace_name: str
    agent_id: str
    agent_name: str


class AdapterMemorySearchRequest(BaseModel):
    namespace_id: str
    agent_id: str | None = None
    session_id: str | None = None
    query: str = Field(..., min_length=3)
    limit: int = Field(default=5, gt=0, le=50)


class AdapterMemoryRead(BaseModel):
    id: str
    memory: str
    resource_kind: str
    space_type: str
    score: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class AdapterMemorySearchResponse(BaseModel):
    adapter: str
    source_system: str
    results: list[AdapterMemoryRead] = Field(default_factory=list)


class AdapterMemoryReviewRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    mark_incorrect: bool = False
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_review_action(self) -> "AdapterMemoryReviewRequest":
        if self.content is None and not self.mark_incorrect:
            raise ValueError("Provide content to update a memory or set mark_incorrect=true")
        if self.content is not None and self.mark_incorrect:
            raise ValueError("Update and mark_incorrect cannot be requested at the same time")
        return self
