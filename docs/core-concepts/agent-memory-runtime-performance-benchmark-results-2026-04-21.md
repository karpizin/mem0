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

## Concurrent Recall Optimization Follow-Up

After the first concurrent baseline, the retrieval hot path was tightened so that each recall request now:

- computes `query_tokens` once per request instead of repeatedly
- reuses precomputed candidate token sets
- reuses precomputed recency scores
- avoids several repeated normalize/tokenize passes during ranking, selection, and explanation building

### Before / After

| Memories | Metric | Before | After | Delta |
| --- | --- | ---: | ---: | ---: |
| `500` | `avg latency` | `1074.4ms` | `913.5ms` | `-160.9ms` |
| `500` | `p95 latency` | `1272ms` | `1110ms` | `-162ms` |
| `500` | `throughput` | `7.346 rps` | `8.5269 rps` | `+1.1809 rps` |
| `1000` | `avg latency` | `1865.625ms` | `1592.25ms` | `-273.375ms` |
| `1000` | `p95 latency` | `2235ms` | `1881ms` | `-354ms` |
| `1000` | `throughput` | `4.1443 rps` | `4.9045 rps` | `+0.7602 rps` |

### Interpretation

- the optimization helped meaningfully at both pool sizes without changing recall output quality
- the gain is larger at `1000` memories, which is a good sign that repeated tokenization/scoring work was a real part of the hot path
- concurrent recall is still the main performance pressure point, but the current path is now materially better than the first baseline

### Current Performance Conclusion

The runtime now shows:

- `good` single-request scaling through `1000` memories
- `good` sequential soak stability through `1000` memories with `0` failures
- `improving but still important` concurrent recall latency under `8-way` load

The next likely performance wins will come from reducing Python-side work further or lowering DB/session contention under parallel recall.

## Storage-Side Tuning Follow-Up

After the retrieval hot-path optimization, the storage/query path was also tightened:

- `episodes` now has composite indexes aligned with recall filters and ordering
- `audit_log` now has composite indexes aligned with feedback lookups and recent-action scans
- `feedback_score_by_entity()` now fast-exits when the namespace has no recall feedback at all, instead of running a large grouped `IN (...)` query across the full candidate pool

### Before / After

These numbers compare the post-hot-path baseline against the same benchmark after storage-side tuning.

| Memories | Metric | Before | After | Delta |
| --- | --- | ---: | ---: | ---: |
| `500` | `avg latency` | `913.5ms` | `862.8ms` | `-50.7ms` |
| `500` | `p95 latency` | `1110ms` | `1015ms` | `-95ms` |
| `500` | `throughput` | `8.5269 rps` | `9.0887 rps` | `+0.5618 rps` |
| `1000` | `avg latency` | `1592.25ms` | `1594.225ms` | `+1.975ms` |
| `1000` | `p95 latency` | `1881ms` | `1727ms` | `-154ms` |
| `1000` | `throughput` | `4.9045 rps` | `4.9116 rps` | `+0.0071 rps` |

### Interpretation

- the storage-side changes helped `500`-memory concurrent load in a clearly measurable way
- at `1000` memories, average latency stayed roughly flat, which suggests the current dominant bottleneck is no longer the no-feedback audit lookup
- however, the `p95` tail improved noticeably at `1000`, which is still a useful production signal
- these changes are also forward-looking: they are more likely to matter in the real Postgres deployment path than in the current SQLite in-process benchmark harness

### Updated Production-Oriented Takeaway

The concurrent recall story now looks like this:

- Python-side hot-path work was a real and important bottleneck
- storage/query tuning gives additional headroom, especially on smaller large-pool loads and latency tails
- the next optimization frontier is increasingly about DB/session contention and query shape under true parallel load, especially for `1000+` candidate pools

## Recall Phase Breakdown

To avoid guessing at the next bottleneck, the concurrent load benchmark now also captures average internal recall phase timings per request.

### `8-way` Concurrent Load, `balanced_runtime`

| Memories | Avg latency | `candidate_fetch` | `candidate_build` | `feedback_lookup` | `ranking` | `selection` | `audit_commit` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `500` | `808.45ms` | `459.175ms` | `64.825ms` | `53.55ms` | `27.5ms` | `71.35ms` | `16.9ms` |
| `1000` | `1588.65ms` | `947.825ms` | `124.55ms` | `81.375ms` | `105.3ms` | `144.925ms` | `30.55ms` |

### Share Of Internal Recall Work

| Memories | `candidate_fetch` | `candidate_build` | `feedback_lookup` | `ranking` | `selection` | `audit_commit` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `500` | `66.23%` | `9.35%` | `7.72%` | `3.97%` | `10.29%` | `2.44%` |
| `1000` | `66.07%` | `8.68%` | `5.67%` | `7.34%` | `10.10%` | `2.13%` |

### Interpretation

- the dominant concurrent bottleneck is now clearly `candidate_fetch`, not ranking or brief assembly
- that holds at both `500` and `1000` memories, which strongly suggests the next real win is in `episodes.list_for_recall()` and its DB/session behavior under parallel load
- `candidate_build` and `selection` are the next-largest slices, but they are still much smaller than fetch pressure
- `feedback_lookup` is no longer dominant after the fast-exit change, though it remains measurable at larger pool sizes
- `audit_commit` is visible but relatively small, so it should not be the first optimization target

### Updated Next Step

The most promising next optimization now is:

- reduce `candidate_fetch` pressure in `EpisodeRepository.list_for_recall()`
- then reassess whether we still need deeper Python-side reductions in candidate construction and selection

## Candidate Fetch Optimization Follow-Up

The next optimization pass changed `EpisodeRepository.list_for_recall()` so it no longer materializes full ORM `Episode` objects for recall gathering.

Instead, the recall path now fetches only the columns it actually needs and returns lightweight row-shaped records for:

- `id`
- `summary`
- `raw_text`
- `importance_hint`
- `created_at`
- `session_id`
- `space_type`

This reduces Python-side ORM construction overhead during the heaviest concurrent phase while keeping the retrieval contract unchanged.

### Before / After

| Memories | Metric | Before | After | Delta |
| --- | --- | ---: | ---: | ---: |
| `500` | `avg latency` | `808.45ms` | `612.5ms` | `-195.95ms` |
| `500` | `p95 latency` | `990ms` | `658ms` | `-332ms` |
| `500` | `throughput` | `9.6071 rps` | `12.4866 rps` | `+2.8795 rps` |
| `1000` | `avg latency` | `1588.65ms` | `1187.025ms` | `-401.625ms` |
| `1000` | `p95 latency` | `1662ms` | `1248ms` | `-414ms` |
| `1000` | `throughput` | `4.9553 rps` | `6.4723 rps` | `+1.517 rps` |

### Updated Phase Breakdown

| Memories | Avg latency | `candidate_fetch` | `candidate_build` | `feedback_lookup` | `ranking` | `selection` | `audit_commit` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `500` | `612.5ms` | `302.5ms` | `60.375ms` | `45.55ms` | `36.425ms` | `63.275ms` | `8.925ms` |
| `1000` | `1187.025ms` | `617.25ms` | `148.5ms` | `54.425ms` | `93.8ms` | `155.875ms` | `11.875ms` |

### Updated Share Of Internal Recall Work

| Memories | `candidate_fetch` | `candidate_build` | `feedback_lookup` | `ranking` | `selection` | `audit_commit` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `500` | `58.5%` | `11.68%` | `8.81%` | `7.04%` | `12.24%` | `1.73%` |
| `1000` | `57.06%` | `13.73%` | `5.03%` | `8.67%` | `14.41%` | `1.1%` |

### Interpretation

- this is the largest concurrent recall improvement so far after the original hot-path cleanup
- `candidate_fetch` is still the largest slice, but it is no longer consuming roughly two-thirds of internal recall time
- the gain holds at both `500` and `1000` memories, which strongly suggests ORM materialization overhead was a real part of the bottleneck
- throughput improved by about `30%` at both pool sizes without changing recall output compactness or failure rate
- the next likely frontier is now lower-level query/session contention or further narrowing of fetched candidate sets, rather than generic Python ranking work

### Updated Production-Oriented Takeaway

The concurrent recall story now looks like this:

- `500 memories`, `8-way concurrency` is now in a much healthier range at about `612ms avg`, `658ms p95`
- `1000 memories`, `8-way concurrency` is still meaningfully heavier, but it improved to about `1187ms avg`, `1248ms p95`
- recall remains stable with `0` failures
- output compactness remains stable, so the win came from runtime efficiency rather than more aggressive truncation

The next performance step should now focus on:

- reducing true DB/session contention under parallel recall
- and only then deciding whether `candidate_build` or `selection` need another optimization pass
