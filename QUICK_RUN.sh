#!/usr/bin/env bash
set -e

echo '1) Build image'
docker build -t garyfang1234/gary-python-web:a03-v1 ./app

echo '2) Push image (requires docker login)'
docker push garyfang1234/gary-python-web:a03-v1

echo '3) Install Argo CD'
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=Available deployment/argocd-server -n argocd --timeout=180s

echo '4) Apply Argo CD Application (repository must already be pushed to GitHub)'
kubectl apply -f argocd/application.yaml

echo '5) Status'
kubectl get application -n argocd
kubectl get pods,svc -n gary-cse644
