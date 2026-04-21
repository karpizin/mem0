from __future__ import annotations

from pydantic import BaseModel, Field


class JobStats(BaseModel):
    by_status: dict[str, int] = Field(default_factory=dict)
    by_type: dict[str, dict[str, int]] = Field(default_factory=dict)
    oldest_pending_age_seconds: float | None = None
    stalled_running_count: int = 0


class MCPStats(BaseModel):
    requests_by_method: dict[str, dict[str, int]] = Field(default_factory=dict)
    tool_calls_by_name: dict[str, dict[str, int]] = Field(default_factory=dict)
    resource_reads_by_name: dict[str, dict[str, int]] = Field(default_factory=dict)
    prompt_requests_by_name: dict[str, dict[str, int]] = Field(default_factory=dict)
    requests_by_client: dict[str, int] = Field(default_factory=dict)
    request_latency_buckets_ms: dict[str, int] = Field(default_factory=dict)
    tool_latency_buckets_ms: dict[str, int] = Field(default_factory=dict)


class RescueQualityStats(BaseModel):
    applied_total: int = 0
    blocked_total: int = 0
    applied_by_trigger: dict[str, int] = Field(default_factory=dict)
    blocked_by_reason: dict[str, int] = Field(default_factory=dict)


class PromotionQualityStats(BaseModel):
    decisions_by_outcome: dict[str, int] = Field(default_factory=dict)
    promote_reasons: dict[str, int] = Field(default_factory=dict)
    session_only_reasons: dict[str, int] = Field(default_factory=dict)
    reject_reasons: dict[str, int] = Field(default_factory=dict)
    novelty_states: dict[str, int] = Field(default_factory=dict)
    signal_flags: dict[str, int] = Field(default_factory=dict)
    rescue: RescueQualityStats = Field(default_factory=RescueQualityStats)


class ObservabilityStats(BaseModel):
    metrics: dict[str, int] = Field(default_factory=dict)
    jobs: JobStats
    mcp: MCPStats = Field(default_factory=MCPStats)
    quality: PromotionQualityStats = Field(default_factory=PromotionQualityStats)
