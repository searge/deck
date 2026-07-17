---
tags:
  - kubernetes
  - kubectl
aliases:
  - kubectl commands
title: kubectl Commands
description: Focused kubectl inspection, logs, exec, port forwarding, dry runs, and safe secret input.
---

# kubectl

Set explicit variables in reusable shell work. Avoid relying on an old current
namespace in copied commands.

```bash
NAMESPACE=default
POD=web-0
CONTAINER=web
```

## Discover And Inspect

```bash
kubectl api-resources --sort-by=name
kubectl -n "$NAMESPACE" get pods -o wide --show-labels
kubectl -n "$NAMESPACE" get deploy,rs,pod
kubectl -n "$NAMESPACE" get events --sort-by=.metadata.creationTimestamp
kubectl -n "$NAMESPACE" describe pod "$POD"
kubectl -n "$NAMESPACE" get pod "$POD" -o yaml
```

Events expire and repeated messages can be aggregated. Correlate them with
current object status, UID, and component evidence.

## Logs

```bash
kubectl -n "$NAMESPACE" logs "$POD" -c "$CONTAINER" --timestamps
kubectl -n "$NAMESPACE" logs "$POD" -c "$CONTAINER" --previous --timestamps
kubectl -n "$NAMESPACE" logs "$POD" --all-containers --prefix
```

`--previous` means the prior container instance in the same Pod, not a previous
Pod with the same name.

## Exec And Debug Sessions

> [!warning] Executes inside a workload
> Even a shell intended for inspection can change files or process state.

```bash
kubectl -n "$NAMESPACE" exec -it "$POD" -c "$CONTAINER" -- /bin/sh
```

Select one Pod explicitly before executing rather than hiding the choice in
command substitution:

```bash
kubectl -n "$NAMESPACE" get pods -l app=web -o name
kubectl -n "$NAMESPACE" exec -it pod/WEB_POD -c "$CONTAINER" -- /bin/sh
```

## Port Forwarding

These commands occupy the foreground. Stop them with `Ctrl-C`; do not add `&`
unless you also own cleanup of the background process.

```bash
kubectl -n "$NAMESPACE" port-forward deployment/myapp 8080:8080
kubectl -n "$NAMESPACE" port-forward service/myservice 8080:80
```

Port forwarding is a diagnostic tunnel through the API path, not evidence that
the Service dataplane works.

## Generate Without Sending

```bash
kubectl create deployment web --image=nginx:1.29 --dry-run=client -o yaml
kubectl create configmap app-config \
  --from-file=config.yaml \
  --dry-run=client -o yaml
kubectl diff -f manifest.yaml
```

`kubectl diff` contacts the server and can exercise admission, but it does not
persist the proposed object.

## Secrets Without Shell Literals

> [!warning] Mutation and sensitive input
> Secret data is base64-encoded in the API object, not inherently encrypted.
> Prefer an external secret workflow where the cluster supports one.

Read a value from standard input so it does not appear in the command line:

```bash
read -rsp 'Database password: ' DB_PASSWORD; printf '\n'
printf '%s' "$DB_PASSWORD" | kubectl -n "$NAMESPACE" create secret generic db-pass \
  --from-file=password=/dev/stdin
unset DB_PASSWORD
```

For registry credentials, use the credential workflow supported by the
environment. Do not commit tokens or demonstrate them as realistic literals.

## Autocomplete

```bash
source <(kubectl completion bash)
alias k=kubectl
complete -o default -F __start_kubectl k
```

Persistent shell configuration is local-machine state and belongs in managed
dotfiles rather than an unreviewed append command.

## References

- [kubectl quick reference](https://kubernetes.io/docs/reference/kubectl/quick-reference/)
- [Debug running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/)
