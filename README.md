# RunScope

RunScope is a self-service experiment and CPU job-management platform for small,
trusted machine-learning workloads.

The current working vertical slice lets a researcher sign in, create a project
and experiment, configure a schema-validated trusted Iris random-forest
template, submit through a PostgreSQL outbox and Redpanda, execute real
scikit-learn training in a separate worker, inspect lifecycle
events/logs/metrics, and download MinIO-backed model, metric JSON, and SVG chart
artifacts. A second trusted template demonstrates live progress, cooperative
cancellation, intentional failure, parent-child retry lineage, notes/tags, and
two-to-five-run comparison. A separate scheduler assigns queued work across two
heartbeating local workers using CPU/memory capacity and database-backed leases.
An authenticated operations view reports dependency latency, scheduler
heartbeat, durable queue/outbox backlog, and worker capacity; the API also
exports Prometheus-compatible metrics and stable correlation-aware errors.
RunScope never accepts arbitrary Python or shell commands.

## Demonstration workflow

1. Start the stack and seed the local data.
2. Sign in as the researcher.
3. Create a project and experiment.
4. Select **Iris random-forest classification**, review its bounded parameters,
   and submit.
5. Open the completed run to inspect its state timeline, metrics chart,
   parameters, logs, and downloadable artifacts.
6. Submit **Slow progress demonstration** and cancel it while it is running.
7. Submit another slow run with intentional failure enabled, then retry it.
8. Save notes/tags and compare the successful classification and retry runs.
9. Open **Workers** to inspect heartbeat age, free capacity, utilization, and
   active leases.
10. Open **Platform health** to inspect dependency probes, queue depth, outbox
    backlog, and allocatable capacity.

## Foundation setup

The target runtime is Python 3.12 and Node 22.22 or newer.

```bash
cp .env.example .env
make setup
make test
docker compose up --build
```

On Windows without GNU Make, run the underlying commands shown in `Makefile`.
The API documentation is available at `http://localhost:8000/docs`; the web app
uses `http://localhost:5173`.

## Local demonstration credentials

These accounts are for the isolated local Compose environment only. Run
`make migrate` and `make seed` before signing in.

| Role | Email | Password |
| --- | --- | --- |
| Viewer | `viewer@runscope.dev` | `ViewerDemo123!` |
| Researcher | `researcher@runscope.dev` | `ResearcherDemo123!` |
| Administrator | `admin@runscope.dev` | `AdminDemo123!` |

RunScope authentication is intentionally demonstrative, not an enterprise
identity system. See `docs/SECURITY.md`.

See [Product requirements](docs/PRODUCT_REQUIREMENTS.md),
[Architecture](docs/ARCHITECTURE.md), and the
[Implementation plan](docs/IMPLEMENTATION_PLAN.md). Deployment and validation
details are in [Kubernetes](docs/KUBERNETES.md),
[Performance](docs/PERFORMANCE.md), [Security](docs/SECURITY.md), and
[Operations](docs/OPERATIONS.md).

RunScope deliberately does not support GPU scheduling, HPC workloads,
distributed training, arbitrary Python, or arbitrary shell commands.
