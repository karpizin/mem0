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


class RecallPerformanceStats(BaseModel):
    requests_observed_total: int = 0
    latency_buckets_ms: dict[str, int] = Field(default_factory=dict)
    candidate_buckets: dict[str, int] = Field(default_factory=dict)
    selected_buckets: dict[str, int] = Field(default_factory=dict)
    external_candidate_buckets: dict[str, int] = Field(default_factory=dict)
    brief_item_buckets: dict[str, int] = Field(default_factory=dict)
    latency_ms_total: int = 0
    latency_ms_max: int = 0
    phase_latency_ms_total: dict[str, int] = Field(default_factory=dict)
    phase_latency_ms_max: dict[str, int] = Field(default_factory=dict)
    phase_latency_buckets_ms: dict[str, dict[str, int]] = Field(default_factory=dict)
    phase_avg_latency_ms: dict[str, float] = Field(default_factory=dict)
    avg_candidate_count: float = 0.0
    avg_selected_count: float = 0.0
    avg_external_candidate_count: float = 0.0
    avg_brief_item_count: float = 0.0


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
    performance: RecallPerformanceStats = Field(default_factory=RecallPerformanceStats)
    mcp: MCPStats = Field(default_factory=MCPStats)
    quality: PromotionQualityStats = Field(default_factory=PromotionQualityStats)
