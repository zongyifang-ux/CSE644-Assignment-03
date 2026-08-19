# CSE644 Assignment 03 — GitOps and Application Observability

**Student:** Gary Fang  
**GitHub:** zongyifang-ux  
**Docker Hub:** garyfang1234  
**Local Kubernetes:** Docker Desktop / kind-based local cluster  
**GitOps tool:** Argo CD

## 1. Application and Architecture
This project extends my earlier CSE644 Docker/Kubernetes work rather than replacing it. It keeps my customized Nginx workload, Python web application on port 8888, and HAProxy edge component. Assignment 03 adds Argo CD as the GitOps controller and Prometheus/Grafana for application observability.

Traffic path for the earlier web workload is `client -> HAProxy -> gary-nginx Service -> Nginx Pods`. The observable workload is `client -> python-web Service -> Python Pods`. The Python application exposes `/health` for Kubernetes probes and `/metrics` for Prometheus.

GitHub is the authoritative desired-state source. Argo CD watches the `k8s/` directory and automatically syncs, prunes removed resources, and self-heals live drift.

## 2. Prerequisites
- Docker Desktop with local Kubernetes enabled
- kubectl
- Git and GitHub account
- Docker Hub account
- Argo CD CLI optional; kubectl is sufficient

## 3. Build and Push the Observable Application
```bash
cd app
docker build -t garyfang1234/gary-python-web:a03-v1 .
docker login
docker push garyfang1234/gary-python-web:a03-v1
```

## 4. Install Argo CD
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=Available deployment/argocd-server -n argocd --timeout=180s
kubectl get pods -n argocd
```

Push this repository to GitHub as `zongyifang-ux/CSE644-Assignment-03`, then create the Argo CD Application:
```bash
kubectl apply -f argocd/application.yaml
kubectl get applications -n argocd
kubectl get pods,svc -n gary-cse644
```

## 5. Validate Application Access
```bash
kubectl port-forward -n gary-cse644 svc/python-web 8888:8888
```
Open `http://localhost:8888` and verify that the page identifies Gary Fang's CSE644 Assignment 03 application.

## 6. Git-Driven Change
Change `APP_MESSAGE` in `k8s/configmap.yaml` from `GitOps v1` to `GitOps v2`, commit, and push:
```bash
git add k8s/configmap.yaml
git commit -m "Update application message through GitOps"
git push
kubectl get application gary-cse644-a03 -n argocd
```
Because the environment variable is injected when Pods start, also change an annotation or image/replica field in the Deployment, or restart via a Git-managed pod-template annotation. The submitted demonstration uses a replica change from 2 to 3, which causes a visible reconciliation without unmanaged cluster changes.

## 7. Live-State Drift and Self-Healing
Create drift intentionally:
```bash
kubectl scale deployment python-web -n gary-cse644 --replicas=1
kubectl get deployment python-web -n gary-cse644
sleep 15
kubectl get deployment python-web -n gary-cse644
```
Git still declares 2 replicas. Argo CD detects the difference and restores the Deployment to 2 replicas because automated self-heal is enabled. This demonstrates that live manual changes do not override Git desired state.

## 8. Controlled Failure and Git-Based Recovery
Create a controlled failure **through Git** by changing the Python image tag in `k8s/python-web.yaml` to a nonexistent tag such as `a03-broken`, then commit and push.

Diagnosis:
```bash
kubectl get pods -n gary-cse644
kubectl describe pod -n gary-cse644 <BROKEN_POD_NAME>
kubectl get application gary-cse644-a03 -n argocd
```
The expected evidence is `ImagePullBackOff`/`ErrImagePull`, showing that Kubernetes cannot pull the declared image. Argo CD has correctly reconciled the desired state, but that desired state itself is invalid.

Recovery must happen in Git. Restore `garyfang1234/gary-python-web:a03-v1`, commit, and push:
```bash
git add k8s/python-web.yaml
git commit -m "Recover application by restoring valid image"
git push
kubectl get pods -n gary-cse644 -w
```
The application returns to Running/Ready after Argo CD syncs the corrected desired state.

## 9. Prometheus Validation
```bash
kubectl port-forward -n gary-cse644 svc/prometheus 9090:9090
```
Open `http://localhost:9090/targets`. The `gary-python-web` target should be UP.

Useful PromQL queries:
```text
gary_app_requests_total
rate(gary_app_requests_total[1m])
rate(gary_app_request_duration_seconds_sum[1m]) / rate(gary_app_request_duration_seconds_count[1m])
```

Generate traffic in another terminal:
```bash
for i in {1..100}; do curl -s http://localhost:8888/ > /dev/null; done
```
The request counter and request rate should increase, demonstrating that monitoring data responds to application workload.

## 10. Grafana Dashboard
```bash
kubectl port-forward -n gary-cse644 svc/grafana 3000:3000
```
Open `http://localhost:3000`. For this local assignment deployment the configured local-only login is `admin` / `cse644-local-only`. Create a dashboard with these panels:
1. Total Requests — `sum(gary_app_requests_total)`
2. Request Rate — `sum(rate(gary_app_requests_total[1m]))`
3. Average Request Latency — `sum(rate(gary_app_request_duration_seconds_sum[1m])) / sum(rate(gary_app_request_duration_seconds_count[1m]))`

The request counter proves application activity, request rate shows workload intensity, and average latency provides a basic view of application response behavior.

## 11. Technical Decisions and Limitations
I selected Argo CD because its Application resource makes desired state, sync status, drift, and recovery easy to demonstrate in a small local cluster. Automated pruning and self-healing make Git authoritative rather than treating Git as only a file backup.

I used direct Prometheus scraping instead of a full Prometheus Operator stack to keep resource use practical for Docker Desktop. The Python application exposes application-level metrics with `prometheus_client`, which provides more meaningful observability than monitoring only Pod status.

This is a local educational environment. Grafana's local demonstration password is not appropriate for production. Production deployments should use external secret management, RBAC, TLS, persistent monitoring storage, and stronger authentication. No real credentials, tokens, kubeconfig files, or private keys are committed to this repository.

## 12. Evidence Checklist
Capture focused screenshots or selected command output for:
- `kubectl get nodes` — local Kubernetes environment
- GitHub repository and commit history
- `kubectl get application -n argocd` — Argo CD Synced/Healthy
- `kubectl get pods,svc -n gary-cse644` — deployed resources
- Browser at localhost:8888 — application access
- Git-driven change and resulting Argo CD sync
- Manual replica drift followed by self-healing
- Broken image commit + ImagePullBackOff diagnosis
- Recovery commit + Running/Ready Pods
- Prometheus Targets page showing target UP
- Prometheus query before/after generated traffic
- Grafana dashboard with request/latency panels
- Cleanup commands and empty namespace/resource verification

## 13. Cleanup
```bash
kubectl delete -f argocd/application.yaml
kubectl delete namespace gary-cse644
kubectl delete namespace argocd
kubectl get ns
kubectl get all -n gary-cse644
```
The final command should report that the namespace is not found after deletion, confirming assignment resources were removed.
