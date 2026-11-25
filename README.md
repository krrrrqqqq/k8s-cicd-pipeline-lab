# k8s-cicd-pipeline-lab

A small Flask service taken all the way from a commit to a running Kubernetes deployment: tests, container image, vulnerability scan, Helm release and rollback.

I built it to practise the delivery path a DevOps team owns. The application is deliberately simple; the pipeline around it is the point.

## What it does

```
git push ─► lint (yamllint, helm lint, kubeconform)
         ─► unit tests (pytest, JUnit report)
         ─► docker build (multi-stage, non-root) ─► push to registry
         ─► Trivy scan (fails on fixable HIGH/CRITICAL)
         ─► helm upgrade --install --atomic  ─► test cluster
                                     manual ─► helm rollback
```

The same pipeline is described twice:

| File | Where it runs |
| --- | --- |
| `.gitlab-ci.yml` | GitLab CI/CD: builds with Docker-in-Docker, pushes to the GitLab Container Registry, deploys to a test cluster through a `KUBE_CONFIG_TEST` file variable |
| `.github/workflows/ci.yml` | GitHub Actions: builds the image, scans it, creates a 3-node kind cluster, deploys the chart and runs a smoke test inside the cluster |

## Repository layout

| Path | Contents |
| --- | --- |
| `app/` | Flask status API with `/healthz`, `/readyz` and Prometheus-format `/metrics`; pytest tests |
| `Dockerfile` | Multi-stage build, virtualenv copied into a slim runtime image, runs as UID 10001 |
| `helm/status-api/` | Helm chart: Deployment with liveness/readiness probes, resource limits, restricted security context, Service, optional Ingress and HPA |
| `cluster/kind-config.yaml` | Local cluster: 1 control-plane + 2 workers |
| `scripts/local-deploy.sh` | Build, load into kind and deploy in one command |

## Run it locally

Requirements: Docker, kind, kubectl, Helm.

```bash
./scripts/local-deploy.sh
kubectl -n status-api port-forward svc/status-api-status-api 8081:80
curl localhost:8081
curl localhost:8081/metrics
```

Rollback after a bad release:

```bash
helm history status-api -n status-api
helm rollback status-api -n status-api
```

## Design notes

- **Zero-downtime rollout.** `maxUnavailable: 0` plus a readiness probe means old pods keep serving until new ones report ready.
- **`--atomic` deploys.** If the release does not become healthy within 3 minutes, Helm rolls it back automatically and the pipeline fails.
- **Hardened pod.** Non-root user, read-only root filesystem, all Linux capabilities dropped, `RuntimeDefault` seccomp profile.
- **Observable by default.** Pods carry `prometheus.io/*` annotations so VictoriaMetrics vmagent can scrape `/metrics` without extra config (see [k8s-observability-lab](https://github.com/krrrrqqqq/k8s-observability-lab)).

## Next steps

- [ ] Mirror the repository to GitLab and run the `.gitlab-ci.yml` pipeline on a self-registered runner
- [ ] Add a `prod` environment with a manual approval gate
- [ ] Move deployment to a pull-based model (Argo CD) and compare with push-based Helm deploys
