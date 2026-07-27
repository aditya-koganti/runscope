# Kubernetes reference deployment

These manifests are an educational reference for the already working Docker
Compose topology. They deploy the API, web UI, scheduler, two stably named
workers, and a one-shot Alembic migration job. They are not a supported,
high-availability distribution.

The manifests deliberately do not bundle stateful dependencies. Before applying
them, provide services named `postgresql`, `redis`, `redpanda`, and `minio` in
the `runscope` namespace:

| Dependency | Expected endpoint | Required behavior |
| --- | --- | --- |
| PostgreSQL | `postgresql:5432` | A created RunScope database/user and durable storage |
| Redis | `redis:6379` | SSE fan-out and scheduler heartbeat keys |
| Redpanda | `redpanda:9092` | Kafka-compatible broker reachable without a public listener |
| MinIO | `minio:9000` | S3-compatible API and a credential allowed to manage the artifact bucket |

Create the namespace and a secret outside source control. The secret must
contain `RUNSCOPE_DATABASE_URL`, `RUNSCOPE_S3_ACCESS_KEY`,
`RUNSCOPE_S3_SECRET_KEY`, and a random `RUNSCOPE_JWT_SECRET`. Set those four
shell variables from the target environment's secret manager, then:

```bash
kubectl apply -f infra/kubernetes/namespace.yaml
kubectl -n runscope create secret generic runscope-secrets \
  --from-literal=RUNSCOPE_DATABASE_URL="$RUNSCOPE_DATABASE_URL" \
  --from-literal=RUNSCOPE_S3_ACCESS_KEY="$RUNSCOPE_S3_ACCESS_KEY" \
  --from-literal=RUNSCOPE_S3_SECRET_KEY="$RUNSCOPE_S3_SECRET_KEY" \
  --from-literal=RUNSCOPE_JWT_SECRET="$RUNSCOPE_JWT_SECRET"
```

Build the two images and load or publish them for the target cluster. The base
Kustomization uses local names:

```bash
docker build --target production -t runscope-python:local -f infra/docker/api.Dockerfile .
docker build -t runscope-web:local -f infra/docker/web.Dockerfile .
kubectl apply -k infra/kubernetes
kubectl -n runscope wait --for=condition=complete job/migrate --timeout=120s
kubectl -n runscope rollout status deployment/api
kubectl -n runscope rollout status deployment/web
kubectl -n runscope port-forward service/web 8080:80
```

For a remote registry, override the two image names/tags in an environment
overlay; do not edit credentials into these manifests. If the migration job
already exists from a previous deployment, delete that completed job before
applying a new migration image.

The API and web use HTTP liveness/readiness probes. Scheduler and worker probes
verify process liveness; their deeper operational state is exposed through the
database-backed worker records and scheduler heartbeat on the platform-health
page. Resource values are conservative demonstration defaults, not measured
capacity recommendations.
