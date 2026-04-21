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


class ObservabilityStats(BaseModel):
    metrics: dict[str, int] = Field(default_factory=dict)
    jobs: JobStats
    mcp: MCPStats = Field(default_factory=MCPStats)
