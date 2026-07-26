# RunScope

RunScope is a self-service experiment and CPU job-management platform for small,
trusted machine-learning workloads.

## Foundation setup

The target runtime is Python 3.12 and Node 22.13 or newer.

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
[Implementation plan](docs/IMPLEMENTATION_PLAN.md).

RunScope deliberately does not support GPU scheduling, HPC workloads,
distributed training, arbitrary Python, or arbitrary shell commands.
