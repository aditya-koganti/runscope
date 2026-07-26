# Performance

No benchmark has been run yet. This document intentionally contains no invented
latency, throughput, error-rate, or queue-delay numbers.

## Planned workload

Locust scenarios will cover project/experiment lists, run creation, run detail,
SSE connections, concurrent submission, and scheduling. Results will record:

- date and machine/container resources;
- service versions and replica counts;
- seeded data and run counts;
- simulated users and spawn rate;
- p50/p95 latency and error rate;
- submission-to-assignment queue delay;
- bottlenecks observed and changes made.

The classification workload is CPU-bound and deliberately small. Load tests will
separate control-plane HTTP pressure from worker execution capacity.

