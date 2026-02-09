---
tags:
  - kubernetes
  - kubectl
aliases:
  - kubectl commands
title: kubectl commands
---

# kubectl

## Autocomplete

### Bash

```bash
source <(kubectl completion bash)

cat >>~/.bashrc <<EOL
source <(kubectl completion bash)
alias k=kubectl
complete -o default -F __start_kubectl k
EOL
exec $SHELL
```

### Zsh

```bash
source <(kubectl completion zsh)
echo '[[ $commands[kubectl] ]] && source <(kubectl completion zsh)' >> ~/.zshrc
```

## Pods

```bash
k get po
k get po -o wide
k get po --show-labels
k get po -n $ns
```

## Deployments

```bash
k get deploy
k get daemonset
k get events
```

## Port forwarding

```bash
k port-forward deployment/myapp 8080:8080
k port-forward svc/myservice 8080:80
k port-forward -n $ns svc/myservice 8088:80 &
```

## Exec into pod

```bash
k exec -it -n $ns $pod -- /bin/sh
```

Select pod by label:

```bash
k exec -it -n $ns \
  $(k get pods --selector=app=web -o jsonpath='{.items[0].metadata.name}' -n $ns) \
  -c $container -- /bin/sh
```

## Secrets

```bash
k create secret generic db-pass \
  --from-literal=password='SECRET'

k create secret docker-registry registry-secret \
  --docker-server="registry.example.com" \
  --docker-username="user" \
  --docker-password="pass" \
  --namespace $ns
```

## Dry run

```bash
k run nginx --image nginx --dry-run=client -o yaml
```

## ConfigMaps

```bash
k -n $ns get cm $configmap -o jsonpath="{.data.key}"
```

## Krew plugins

```bash
k krew install ctx
k krew install ns
k krew list
```

## Cluster info

```bash
k cluster-info
k cluster-info dump
k top node
```
