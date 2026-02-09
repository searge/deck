---
tags:
  - kubernetes
  - helm
aliases:
  - Helm commands
title: Helm commands
description: Helm repo management, install, and status commands.
---

# helm

## Repo management

```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update argo
```

## Install

```bash
helm install my-release argo/argo-cd --version 5.16.13
```

## Status

```bash
helm list
helm status $release
```

## References

- [kubectl cheatsheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [spacelift k8s cheatsheet](https://spacelift.io/blog/kubernetes-cheat-sheet)
