---
tags:
  - gcp
  - cloud
aliases:
  - Google Cloud Platform
title: Google Cloud Platform
---

# gcp

## Auth

```bash
gcloud auth login
gcloud auth configure-docker
gcloud auth list
gcloud cheat-sheet
```

## Config

```bash
gcloud config set compute/region $region
gcloud config set compute/zone $zone
gcloud config list
gcloud config config-helper --format=json
```

```bash
gcloud info --format='value(installation.sdk_root)'
gcloud info --format='value(config.paths.global_config_dir)'
```

## Compute

```bash
gcloud compute zones list
gcloud compute regions list
gcloud compute project-info describe --project $project
```

### SSH to instance

```bash
gcloud compute ssh \
  --zone "$zone" "$instance" \
  --project "$project"
```

## GKE

### Install components

```bash
gcloud components install kubectl gke-gcloud-auth-plugin
```

### Create cluster

```bash
gcloud container clusters create $cluster \
  --zone $zone \
  --machine-type e2-medium --num-nodes 2
```

### Get credentials

```bash
gcloud container clusters get-credentials $cluster \
  --zone $zone \
  --project $project
```

### Delete cluster

```bash
gcloud container clusters delete $cluster \
  --zone $zone \
  --project $project
```

### Delete project

```bash
gcloud projects delete $project
# Undo within grace period:
gcloud projects undelete $project
```
