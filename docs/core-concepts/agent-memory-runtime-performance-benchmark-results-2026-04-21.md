# Agent Memory Runtime Performance Benchmark Results

`Date:` `2026-04-21`

## Scope

This report captures the current recall performance baseline after:

- high-density retrieval regressions
- performance observability instrumentation
- multi-scenario performance benchmark pool

The results below were measured against the current runtime code using an in-process `TestClient` harness, which isolates memory-runtime algorithm behavior from container drift or external provider variance.

## Scenarios

The benchmark pool currently includes:

- `balanced_runtime`
- `procedure_heavy`
- `session_pressure`
- `integration_mix`

Each scenario combines a small set of relevant durable facts with a much larger pool of low-value noise memories.

## 200-Memory Multi-Scenario Pool

Configuration:

- `4` scenarios
- `200` memories per scenario
- `5` recall queries per scenario

### Overall

| Metric | Value |
| --- | ---: |
| `avg latency` | `22ms` |
| `p50 latency` | `23ms` |
| `p95 latency` | `25ms` |
| `max latency` | `25ms` |
| `avg candidate count` | `200` |
| `avg selected count` | `2.0` |
| `avg brief chars` | `298.5` |

### Per Scenario

| Scenario | Avg latency | P95 latency | Avg candidates | Avg selected | Avg brief chars |
| --- | ---: | ---: | ---: | ---: | ---: |
| `balanced_runtime` | `23.8ms` | `32ms` | `200` | `2.2` | `249.4` |
| `procedure_heavy` | `25.2ms` | `32ms` | `200` | `2.0` | `200.2` |
| `session_pressure` | `19.4ms` | `25ms` | `200` | `2.8` | `365.6` |
| `integration_mix` | `21.0ms` | `31ms` | `200` | `2.8` | `380.8` |

### Interpretation

- recall latency remains low and stable on `200`-memory pools
- candidate pressure grows exactly to the pool size, as expected
- selected item count stays tightly bounded around `2-3`
- brief size does not scale with memory pool size, which is a strong sign that compactness controls are working

## Larger Single-Scenario Scaling Runs

To get a clearer scaling curve without waiting for a full `4 x scenario` pool at larger sizes, the `balanced_runtime` scenario was also run separately at `500` and `1000` memories.

### Results

| Memories | Avg latency | P50 | P95 | Max | Avg selected | Avg brief chars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `200` | `23.8ms` | `19ms` | `32ms` | `32ms` | `2.2` | `249.4` |
| `500` | `49.4ms` | `36ms` | `71ms` | `71ms` | `2.2` | `249.4` |
| `1000` | `96.8ms` | `78ms` | `139ms` | `139ms` | `2.2` | `249.4` |

### Interpretation

- latency growth is roughly linear between `200`, `500`, and `1000` candidate memories
- even at `1000` memories, the average recall stays under `100ms` in the current in-process benchmark path
- `selected_count` remains stable
- `brief_chars` remains stable

This suggests the main retrieval path is currently scaling well for at least the first `1000` candidates.

## Operational Note

The full multi-scenario pool at `500+` memories per scenario already becomes a heavy benchmark workload in its own right because it creates a large number of ingestion, consolidation, and lifecycle jobs. That is a useful finding itself:

- memory retrieval still looks healthy
- but the benchmark harness and job-processing contour should be optimized further before we rely on full `4-scenario x 1000-memory` runs as a routine regression gate

## Current Conclusion

Current recall scaling looks `good` for the first production-oriented baseline:

- compact selection remains under control
- brief size remains bounded
- latency remains low through `200`-memory multi-scenario pools
- latency remains acceptable and predictable through `1000`-memory single-scenario runs

## Soak Benchmark

To measure repeated-recall stability on large memory pools, an additional soak benchmark was run on the `balanced_runtime` scenario.

Configuration:

- `50` sequential recall requests
- same large durable/noise memory pool reused across the whole run

### Results

| Memories | Failures | Failure rate | Avg latency | P50 | P95 | Max | Avg selected | Avg brief chars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `500` | `0` | `0.0` | `69.9ms` | `69ms` | `72ms` | `82ms` | `1.0` | `121` |
| `1000` | `0` | `0.0` | `136.34ms` | `134ms` | `148ms` | `156ms` | `1.0` | `121` |

### Interpretation

- repeated recall remained stable with `0` failures at both `500` and `1000` memories
- latency under soak grows roughly linearly between `500` and `1000`
- recall output remained extremely stable:
  - `selected_count` stayed fixed at `1`
  - `brief_chars` stayed fixed at `121`

This suggests the retrieval path is not only scaling reasonably by pool size, but also remains stable under repeated sequential use on the same namespace.

## Recommended Next Steps

1. Optimize the benchmark harness so that full `500/1000` multi-scenario pools can complete faster.
2. Add a true load/concurrency benchmark rather than only sequential recall measurements.
3. After that, compare in-process benchmark numbers with live container benchmarks on the same scenario pack.

## Concurrent Load Benchmark

To measure concurrent recall pressure on the same large namespace, an additional load benchmark was run against the current runtime code in `in-process` mode.

Configuration:

- `balanced_runtime`
- `8` concurrent recall workers
- `5` rounds
- `40` total recall requests per run

The runs below used clean temp SQLite DSNs to avoid stale local schema drift from older benchmark databases.

### Results

| Memories | Total requests | Failures | Failure rate | Throughput | Avg latency | P50 | P95 | Max | Avg selected | Avg brief chars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `500` | `40` | `0` | `0.0` | `7.346 rps` | `1074.4ms` | `1038ms` | `1272ms` | `1295ms` | `1.0` | `121` |
| `1000` | `40` | `0` | `0.0` | `4.1443 rps` | `1865.625ms` | `1955ms` | `2235ms` | `2236ms` | `1.0` | `121` |

### Interpretation

- under concurrent recall pressure, the runtime remained stable with `0` failures at both `500` and `1000` memories
- latency is materially higher than the sequential benchmark path, which is expected under `8` parallel recall requests against the same in-process app/database
- throughput still remains usable for this early baseline, but the numbers now show a real next-stage optimization frontier:
  - sequential scaling is already healthy
  - concurrent recall is now the main pressure point to watch
- output compactness remained perfectly stable:
  - `selected_count` stayed fixed at `1`
  - `brief_chars` stayed fixed at `121`

### Updated Conclusion

The current retrieval path looks strong on three different axes:

- `single-request scaling`: good through `1000` memories
- `sequential soak stability`: good through `1000` memories with `0` failures
- `concurrent recall stability`: good through `1000` memories with `0` failures, though latency under concurrency is now high enough that it should become the next optimization focus
