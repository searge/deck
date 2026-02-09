---
tags:
  - kubernetes
  - snippets
aliases:
  - Kubernetes hacks
title: Kubernetes hacks
---

# kubernetes

- [[kubectl]]
- [[helm]]

## Basics

```bash
alias k=kubectl

k version --short
k cluster-info
k get nodes
```

## Namespaces and context

```bash
k get namespaces
k config get-contexts
k config use-context $context
k config set-context --current --namespace $ns
k config delete-context $context
k config delete-cluster $cluster
```

## Overview

```bash
k config view -o yaml
k get all -A
```
