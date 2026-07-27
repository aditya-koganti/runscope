# Load scenarios

The Locust workload authenticates as the local-only researcher account and uses
an existing experiment. Set `RUNSCOPE_LOAD_EXPERIMENT_ID` to make the dataset
stable; otherwise the newest visible experiment is selected.

Read-only control-plane and SSE run:

```bash
locust -f tests/load/locustfile.py \
  --host http://localhost:8000/api/v1 \
  --headless --users 5 --spawn-rate 1 --run-time 30s \
  --tags read sse
```

Mutating submission and scheduler-delay run:

```bash
RUNSCOPE_LOAD_ENABLE_MUTATIONS=true \
locust -f tests/load/locustfile.py \
  --host http://localhost:8000/api/v1 \
  --headless --users 2 --spawn-rate 1 --run-time 20s \
  --tags submission scheduler
```

Override `RUNSCOPE_LOAD_EMAIL` and `RUNSCOPE_LOAD_PASSWORD` when the local demo
credentials have been changed. Mutating scenarios create trusted two-second
demonstration runs; they never send code, commands, images, or file paths.
