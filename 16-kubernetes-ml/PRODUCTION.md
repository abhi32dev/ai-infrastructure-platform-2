# Production Readiness — Kubernetes for ML Workloads

## Current state
Real `kind` cluster, Deployment/Service/HPA with readiness/liveness
probes. Found and fixed a real bug (health always returned 200, invisible
to K8s probes) and documented a second real limitation (HALF_OPEN reads
healthy without active re-check). 6 tests including live-cluster and
deterministic unit coverage.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| `kind` (Kubernetes-in-Docker), not a managed cluster | Free, local, real Kubernetes API — not a simulation | Doesn't exercise real cloud-provider-specific behaviors (IAM-integrated service accounts, cloud load balancer provisioning, real node autoscaling) |
| `host.docker.internal` for reaching Ollama | Lets the containerized app reach a host-run model server without containerizing Ollama itself | Not how a real deployment would work — production would run the model server in-cluster or as a proper external service with a stable DNS name |
| HPA configured but not exercised under real load | No metrics-server load-testing was performed in this demo | The HPA's `minReplicas`/`maxReplicas`/target-utilization config is verified correct via `kubectl get hpa`, but autoscaling behavior itself wasn't proven under generated load |

## What's missing for real production use
- **Metrics-server + load-tested HPA** — the HPA is configured correctly
  but never actually triggered a scale event in this demo; a production
  validation needs a load test proving it scales up and back down
  correctly
- **The active-health-check fix for HALF_OPEN** — documented as a known
  limitation, not fixed: a production readiness probe needs to actively
  ping the downstream when the breaker is HALF_OPEN, not just report
  passively-observed state
- **Network policies** — no `NetworkPolicy` resources restrict pod-to-pod
  traffic; a production cluster needs explicit network segmentation
- **Resource requests/limits tuning** — current values (`100m`/`128Mi`
  requests, `500m`/`256Mi` limits) are reasonable demo defaults, not
  load-tested/right-sized for real traffic

## Scaling considerations
- This demo runs 2 replicas on a single-node `kind` cluster; a real
  deployment needs multi-node clusters with pod anti-affinity rules so
  replicas don't co-locate on a single node (defeating the redundancy
  purpose)
- GPU scheduling (the actual "GPU scheduling" theme from the market
  research) isn't demonstrated — this deploys a CPU-bound serving
  wrapper; real ML workload scheduling needs `nvidia.com/gpu` resource
  requests and a GPU-aware scheduler, not exercised here

## Security & compliance considerations
- No `NetworkPolicy`, no `PodSecurityPolicy`/`PodSecurityStandards`
  enforcement, no image scanning in the build pipeline — all real
  production Kubernetes security requirements not addressed in this local
  demo
- The Docker image runs as root by default (no explicit
  `securityContext` with a non-root user) — a real deployment should set
  this explicitly

## Operational readiness
- No Kubernetes-native logging/monitoring stack (e.g., a Prometheus
  Operator + `ServiceMonitor`) wired to this deployment, though project
  13 demonstrates the underlying pattern separately
- No rolling-update strategy tuning (`maxSurge`/`maxUnavailable`) — using
  Kubernetes Deployment defaults, not validated for this specific
  service's tolerance for brief unavailability during updates
