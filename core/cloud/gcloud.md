---
tags:
  - gcp
  - cloud
  - kubernetes
aliases:
  - Google Cloud Platform
  - gcloud CLI
title: Google Cloud Platform
description: GCP CLI reference, project management, compute, GKE, and authentication.
---

# gcloud

Google Cloud Platform documentation for the `gcloud` CLI. Auth, compute resources, container clusters, and common operations.

## Prerequisites

```bash
# Install gcloud SDK
# macOS (Homebrew)
brew install google-cloud-sdk

# Linux (apt/snap/other)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Verify installation
gcloud --version
```

## Authentication

```bash
# Interactive login (opens browser)
gcloud auth login

# Login with service account
gcloud auth activate-service-account --key-file=/path/to/key.json

# List authenticated accounts
gcloud auth list

# Set active account
gcloud config set account <account>

# Print access token (for APIs)
gcloud auth print-access-token

# Configure Docker to authenticate with GCR
gcloud auth configure-docker
gcloud auth configure-docker us-docker.pkg.dev,eu-docker.pkg.dev

# Logout
gcloud auth revoke <account>
```

## Configuration

```bash
# Set project
gcloud config set project <project-id>

# Set compute region
gcloud config set compute/region us-central1

# Set compute zone
gcloud config set compute/zone us-central1-a

# List all settings
gcloud config list

# View config in JSON format
gcloud config config-helper --format=json

# Get specific paths
gcloud info --format='value(installation.sdk_root)'
gcloud info --format='value(config.paths.global_config_dir)'
```

### Named Configurations

For managing multiple projects/accounts, use named configurations instead of constantly switching accounts:

```bash
# Create a configuration for each project/account combo
gcloud config configurations create sqor-dev
gcloud config configurations create sqor-prod
gcloud config configurations create personal-account

# Activate and configure sqor-dev
gcloud config configurations activate sqor-dev
gcloud config set project sqor-dev-463118
gcloud config set account terraform@sqor-dev-463118.iam.gserviceaccount.com
gcloud config set compute/zone us-central1-a

# Activate and configure sqor-prod
gcloud config configurations activate sqor-prod
gcloud config set project sqor-prod-xxxxx
gcloud config set account terraform@sqor-prod-xxxxx.iam.gserviceaccount.com
gcloud config set compute/zone us-central1-a

# Activate and configure personal account
gcloud config configurations activate personal-account
gcloud config set project my-personal-project
gcloud config set account user@gmail.com
gcloud config set compute/zone us-central1-a

# List configurations
gcloud config configurations list

# Delete unused configuration
gcloud config configurations delete <name>
```

**Key points:**
- Each configuration bundles account + project + region/zone together
- Switch entire context with one command: `gcloud config configurations activate <name>`
- Always verify active config before running commands: `gcloud config list`

### Using Configurations with Kubernetes

**Critical:** When switching configurations for kubectl, always re-fetch cluster credentials:

```bash
# Switch to sqor-dev config
gcloud config configurations activate sqor-dev

# UPDATE kubeconfig (this copies new credentials into ~/.kube/config)
gcloud container clusters get-credentials sqor-gke-autopilot-dev --zone us-central1-a

# Now kubectl uses the correct account
kubectl -n mongodb get svc mongodb-lb
```

Without `get-credentials`, kubectl uses stale credentials from kubeconfig.

### Troubleshooting Multiple Accounts

If kubectl still shows wrong user after switching:

```bash
# Check current kubeconfig context and user
kubectl config current-context
kubectl config view | grep -A5 "current-context"

# See all contexts
kubectl config get-contexts

# Manual context switch (as fallback)
kubectl config use-context <context-name>

# Force full re-authentication
gcloud container clusters get-credentials <cluster> --zone <zone> --force-update-auth
```

**The flow:**

1. `gcloud config configurations activate <name>` — switches gcloud CLI
2. `gcloud container clusters get-credentials` — updates kubeconfig with new credentials
3. kubectl now uses the correct service account/user

## Projects

```bash
# List projects
gcloud projects list

# Describe a project
gcloud projects describe <project-id>

# Create a project
gcloud projects create <project-id>

# Set billing account
gcloud billing projects link <project-id> --billing-account=<account-id>

# Undelete a project (within grace period)
gcloud projects undelete <project-id>

# Delete a project (permanent after 30 days)
gcloud projects delete <project-id>
```

## Compute Engine

### Zones and Regions

```bash
# List available zones
gcloud compute zones list

# List available regions
gcloud compute regions list

# Describe a region
gcloud compute regions describe <region>

# Describe a zone
gcloud compute zones describe <zone>

# Get default zone
gcloud config get-value compute/zone
```

### Instances

```bash
# List instances
gcloud compute instances list
gcloud compute instances list --filter="zone:<zone>"

# Create instance
gcloud compute instances create <instance-name> \
  --zone=<zone> \
  --machine-type=e2-medium \
  --image-family=debian-11 \
  --image-project=debian-cloud \
  --boot-disk-size=20GB

# SSH into instance
gcloud compute ssh <instance-name> \
  --zone=<zone> \
  --project=<project-id>

# Copy files to instance
gcloud compute scp <local-path> <instance-name>:/remote/path \
  --zone=<zone>

# Copy files from instance
gcloud compute scp <instance-name>:/remote/path <local-path> \
  --zone=<zone>

# Start/stop instance
gcloud compute instances start <instance-name> --zone=<zone>
gcloud compute instances stop <instance-name> --zone=<zone>

# Delete instance
gcloud compute instances delete <instance-name> --zone=<zone>

# Get serial port output (logs)
gcloud compute instances get-serial-port-output <instance-name> --zone=<zone>
```

### Disks

```bash
# List disks
gcloud compute disks list

# Create disk
gcloud compute disks create <disk-name> \
  --zone=<zone> \
  --size=100GB \
  --type=pd-standard

# Attach disk to instance
gcloud compute instances attach-disk <instance-name> \
  --disk=<disk-name> \
  --zone=<zone>

# Delete disk
gcloud compute disks delete <disk-name> --zone=<zone>
```

### Snapshots

```bash
# Create snapshot from disk
gcloud compute disks snapshot <disk-name> \
  --snapshot-names=<snapshot-name> \
  --zone=<zone>

# List snapshots
gcloud compute snapshots list

# Delete snapshot
gcloud compute snapshots delete <snapshot-name>
```

## Kubernetes Engine (GKE)

### Installation

```bash
# Install kubectl component
gcloud components install kubectl

# Install GKE authentication plugin
gcloud components install gke-gcloud-auth-plugin

# Update components
gcloud components update
```

### Cluster Management

```bash
# Create cluster
gcloud container clusters create <cluster-name> \
  --zone=<zone> \
  --num-nodes=3 \
  --machine-type=e2-medium \
  --enable-stackdriver-kubernetes \
  --addons=HorizontalPodAutoscaling,HttpLoadBalancing

# List clusters
gcloud container clusters list

# Describe cluster
gcloud container clusters describe <cluster-name> \
  --zone=<zone>

# Get cluster credentials (update kubeconfig)
gcloud container clusters get-credentials <cluster-name> \
  --zone=<zone> \
  --project=<project-id>

# Resize cluster
gcloud container clusters resize <cluster-name> \
  --num-nodes=5 \
  --zone=<zone>

# Update cluster (version, settings)
gcloud container clusters update <cluster-name> \
  --zone=<zone> \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10

# Delete cluster
gcloud container clusters delete <cluster-name> \
  --zone=<zone>
```

### Node Pools

```bash
# Create node pool
gcloud container node-pools create <pool-name> \
  --cluster=<cluster-name> \
  --zone=<zone> \
  --machine-type=e2-medium \
  --num-nodes=2

# List node pools
gcloud container node-pools list \
  --cluster=<cluster-name> \
  --zone=<zone>

# Delete node pool
gcloud container node-pools delete <pool-name> \
  --cluster=<cluster-name> \
  --zone=<zone>
```

## Container Registry

```bash
# Build image with Cloud Build
gcloud builds submit --tag gcr.io/<project-id>/<image-name>:<tag> .

# Push image
docker tag <local-image> gcr.io/<project-id>/<image-name>:<tag>
docker push gcr.io/<project-id>/<image-name>:<tag>

# List images
gcloud container images list

# List image tags
gcloud container images list-tags gcr.io/<project-id>/<image-name>

# Delete image
gcloud container images delete gcr.io/<project-id>/<image-name>:<tag>

# Configure authentication
gcloud auth configure-docker gcr.io
```

## Service Accounts

```bash
# List service accounts
gcloud iam service-accounts list

# Create service account
gcloud iam service-accounts create <sa-name> \
  --display-name="<display-name>"

# Grant role to service account
gcloud projects add-iam-policy-binding <project-id> \
  --member=serviceAccount:<sa-email> \
  --role=roles/container.developer

# Create key for service account
gcloud iam service-accounts keys create key.json \
  --iam-account=<sa-email>

# Delete service account
gcloud iam service-accounts delete <sa-email>
```

## Billing

```bash
# List billing accounts
gcloud billing accounts list

# Set default billing account
gcloud config set billing/quota_project <project-id>

# View billing info for project
gcloud billing projects describe <project-id>
```

## Deployment

```bash
# Deploy with Cloud Run
gcloud run deploy <service-name> \
  --image=gcr.io/<project-id>/<image-name>:<tag> \
  --platform=managed \
  --region=us-central1

# Deploy with App Engine
gcloud app deploy

# Deploy with Deployment Manager
gcloud deployment-manager deployments create <deployment-name> \
  --config=config.yaml
```

## Debugging and Logs

```bash
# View instance logs
gcloud compute instances get-serial-port-output <instance-name> \
  --zone=<zone>

# Tail Cloud Logging
gcloud logging read --limit=50

# Filter logs
gcloud logging read "resource.type=k8s_cluster" --limit=100

# Write to logs
gcloud logging write <log-name> "message"
```

## Tips

- Use `gcloud help <command>` for command-specific help
- Set defaults in config to avoid repeated flags
- Use `gcloud cheat-sheet` for quick reference
- Create multiple configurations for dev/staging/prod environments
- Always verify active project before running commands: `gcloud config list`
