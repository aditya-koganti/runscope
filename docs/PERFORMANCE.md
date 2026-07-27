# Performance

## 2026-07-27 local benchmark

Two short Locust smoke benchmarks ran against the complete nine-service Docker
Compose topology. Docker Desktop 26.1.1 exposed 8 CPUs and 3,844,943,872 bytes
(about 3.58 GiB) of memory to Linux containers. The topology had one API, one
scheduler, two workers, PostgreSQL, Redis, Redpanda, MinIO, and the web proxy.
The database contained 16 projects, 16 experiments, and 24 runs before the
mutating scenario.

The read/SSE scenario used 5 users, a spawn rate of 1 user/second, and a
30-second duration. It completed 106 requests with no failures:

| Request | Count | Average | p50 | p95 | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| All read/SSE requests | 106 | 26 ms | 18 ms | 57 ms | 229 ms |
| Sign in | 5 | 165 ms | 140 ms | 230 ms | 229 ms |
| Experiments list | 29 | 18 ms | 17 ms | 27 ms | 31 ms |
| Projects list | 24 | 17 ms | 17 ms | 23 ms | 24 ms |
| Platform summary | 15 | 26 ms | 24 ms | 40 ms | 42 ms |
| Runs list | 5 | 24 ms | 25 ms | 29 ms | 29 ms |
| Run detail | 23 | 17 ms | 16 ms | 29 ms | 34 ms |
| SSE preamble | 5 | 14 ms | 15 ms | 17 ms | 17 ms |

The opt-in mutating scenario used 2 users, a spawn rate of 1 user/second, and a
20-second duration. It completed 55 observations with no failures:

| Request or observation | Count | Average | p50 | p95 | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: |
| Trusted run submission | 19 | 50 ms | 46 ms | 87 ms | 87 ms |
| Assignment status poll | 22 | 18 ms | 18 ms | 25 ms | 27 ms |
| Submission to assignment | 8 | 401 ms | 460 ms | 680 ms | 681 ms |

The mutating run created only registered two-second demonstration jobs. An
immediate post-run snapshot contained 43 runs: 34 succeeded, 4 failed,
4 cancelled, and 1 still running. It had no queued runs.

## Interpretation

These measurements are a reproducible smoke baseline, not a capacity claim.
There were no request or assignment failures and no saturation signal at this
small concurrency. Argon2 password verification made sign-in the slowest HTTP
operation, as expected. The platform summary was the slowest authenticated
read because it aggregates durable queue, worker, scheduler, and outbox state.
No tuning was performed because the run did not identify a correctness or
capacity bottleneck.

Longer soak tests, cold-cache trials, larger seeded datasets, worker CPU
saturation, dependency fault injection, and percentile comparison across
repeated runs remain future work.

## Reproduce

The scenarios live in `tests/load/locustfile.py`. Read-only access and the SSE
preamble are the default:

```bash
make load-test
```

Mutating execution is explicitly enabled and accepts only the registered slow
demonstration template:

```bash
make load-test-mutations
```

The classification workload is CPU-bound and deliberately small. Load tests will
separate control-plane HTTP pressure from worker execution capacity.
