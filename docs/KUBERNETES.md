# Kubernetes deployment

Docker Compose remains RunScope's reference development environment. The
manifests under `infra/kubernetes` demonstrate how to separate the stateless
control plane, scheduler, worker pool, and migration job in Kubernetes while
keeping secrets external.

## Scope

- API and web Deployments expose HTTP probes and bounded resource settings.
- The scheduler is a single Deployment because the current lease scheduler is
  intentionally simple.
- Workers use a two-replica StatefulSet so broker consumer identities remain
  stable across pod restarts.
- The migration Job upgrades PostgreSQL before application rollout.
- Containers run without privilege escalation, drop Linux capabilities, use
  read-only root filesystems, and do not mount service-account tokens.

## Stateful dependencies

PostgreSQL, Redis, Redpanda, and MinIO are not installed by the base manifests.
Their durability, backup, upgrade, authentication, and availability policies are
operator decisions that RunScope should not conceal inside application YAML.
The exact in-cluster service contracts and local commands are documented in
`infra/kubernetes/README.md`.

This reference does not add TLS, ingress, network policy, PodDisruptionBudgets,
autoscaling, managed database operators, or backup automation. Those omissions
are deliberate limitations, not production recommendations.
