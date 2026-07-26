# Limitations

RunScope is a local educational platform for trusted, small CPU workloads.

- No GPUs, accelerator topology, HPC queues, gang scheduling, or distributed
  neural-network training.
- No arbitrary Python, shell, image, dependency, or user dataset execution.
- No production multi-tenancy, SSO/MFA, quotas, billing, policy engine, or
  organization isolation.
- The initial scheduler uses simplified CPU/memory bin packing and leases; it
  does not model NUMA, disk, network, preemption, fairness, or autoscaling.
- Compose dependencies are single-node and not highly available.
- Kubernetes examples are local/reference manifests, not a supported production
  distribution.
- SSE uses REST recovery and is not a permanent event archive.
- Demonstration passwords and infrastructure defaults are safe only on a local,
  isolated developer machine.

Verified environment-specific limitations and known bugs will be appended during
implementation rather than predicted.

