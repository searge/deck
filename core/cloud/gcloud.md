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

Each configuration bundles account + project + region/zone. One command switches the entire context — no browser re-auth needed, tokens are stored locally.

> Note: configuration names allow only lowercase letters, digits, and hyphens (no underscores).

```bash
# Create a configuration (do once per account/project combo)
gcloud config configurations create <name>
gcloud config configurations activate <name>
gcloud config set account <email>
gcloud config set project <project-id>
gcloud config set compute/region <region>   # e.g. europe-west9
gcloud config set compute/zone <zone>       # e.g. europe-west9-a

# Switch between configurations
gcloud config configurations activate <name>

# List all configurations
gcloud config configurations list

# Delete a configuration
gcloud config configurations delete <name>
```

**Region reference:**

| Location               | Region             | Zone               |
|------------------------|--------------------|--------------------|
| Paris                  | `europe-west9`     | `europe-west9-a`   |
| Warsaw (closest to UA) | `europe-central2`  | `europe-central2-a`|
| US Central             | `us-central1`      | `us-central1-a`    |

### Quick Switching with Fish Shell

Add to `~/.config/fish/conf.d/gcloud.fish`:

```fish
# Switch config + sync ADC quota project, suppress noisy warnings
function gca
    gcloud config configurations activate $argv[1] 2>/dev/null
    set -l project (gcloud config get project 2>/dev/null)
    if test -n "$project"
        gcloud auth application-default set-quota-project $project --quiet 2>/dev/null
    end
    echo "Active: "(gcloud config get account 2>/dev/null)" / $project"
end

# Tab completions
complete -c gca -f -a "(gcloud config configurations list --format='value(name)')"
```

```bash
gca work      # → Active: user@company.com / my-project-id
gca personal  # → Active: user@gmail.com / personal-project
```

The function suppresses two common noisy warnings:

- `WARNING: Your active project does not match the quota project in your local Application Default Credentials file` — fixed by syncing ADC quota project automatically
- `[environment: untagged]` — cosmetic GCP tag prompt, safely ignored

### Per-Session Isolation (without affecting global config)

Use `CLOUDSDK_ACTIVE_CONFIG_NAME` to override the active config for a single terminal only:

```bash
# Fish
set -x CLOUDSDK_ACTIVE_CONFIG_NAME work
gcloud config list  # confirms "work" is active in this terminal only

# Unset to return to global active config
set -e CLOUDSDK_ACTIVE_CONFIG_NAME
```

### Using Configurations with Kubernetes

**Critical:** When switching configurations for kubectl, always re-fetch cluster credentials:

```bash
# Switch config
gcloud config configurations activate <name>

# Update kubeconfig with credentials for the new account
gcloud container clusters get-credentials <cluster-name> --zone <zone>

# Now kubectl uses the correct account
kubectl get pods -n <namespace>
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

## Terraform

### Authentication options

There are three ways to authenticate the Terraform Google provider, in order of preference for local development:

#### 1. Application Default Credentials (ADC) — recommended for local dev

```bash
gcloud auth application-default login
```

Terraform picks up ADC automatically — no `credentials` field needed in the provider block. Works with named configurations.

#### 2. Service account impersonation — no key files, audit-friendly

```bash
# One-time setup: grant yourself the Token Creator role
gcloud iam service-accounts add-iam-policy-binding terraform@<project>.iam.gserviceaccount.com \
  --member="user:<your-email>" \
  --role="roles/iam.serviceAccountTokenCreator"
```

```hcl
provider "google" {
  impersonate_service_account = "terraform@<project>.iam.gserviceaccount.com"
}
```

Or via env var (useful for CI or switching SAs without touching .tf files):

```bash
export GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=terraform@<project>.iam.gserviceaccount.com
```

#### 3. Service account key file — avoid if possible, last resort for CI without Workload Identity

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### Environment variables

Avoid hardcoding values in provider blocks — use env vars instead. Terraform Google provider reads these automatically:

| Variable                             | Equivalent provider field      | Notes                             |
|--------------------------------------|--------------------------------|-----------------------------------|
| `GOOGLE_PROJECT`                     | `project`                      | Default project for all resources |
| `GOOGLE_REGION`                      | `region`                       | Default region                    |
| `GOOGLE_ZONE`                        | `zone`                         | Default zone                      |
| `GOOGLE_APPLICATION_CREDENTIALS`     | `credentials`                  | Path to SA key JSON               |
| `GOOGLE_IMPERSONATE_SERVICE_ACCOUNT` | `impersonate_service_account`  | SA email to impersonate           |

### `GOOGLE_CLOUD_QUOTA_PROJECT`

Controls which project is billed for API calls made by ADC. Needed when:

- Your user account has access to many projects and GCP can't determine which one to charge
- You get `quota exceeded` or `billing not enabled` errors despite the target project being fine
- You're running Terraform with ADC and the project in context differs from the one being managed

```bash
# Set quota project to the project you're deploying into
export GOOGLE_CLOUD_QUOTA_PROJECT=<project-id>
terraform plan
```

When **not** to set it:

- Using a service account key (`GOOGLE_APPLICATION_CREDENTIALS`) — quota project is inferred from the SA
- Using impersonation — same, inferred from the target SA's project

### Tips & Tricks

#### Minimal provider block — let env vars do the work

```hcl
provider "google" {}

provider "google-beta" {}
```

#### Per-workspace project isolation with Fish

```fish
# Activate gcloud config + set Terraform env vars in one step
function tf-env
    gca $argv[1]
    set -x GOOGLE_PROJECT (gcloud config get project 2>/dev/null)
    set -x GOOGLE_CLOUD_QUOTA_PROJECT $GOOGLE_PROJECT
    set -x GOOGLE_REGION (gcloud config get compute/region 2>/dev/null)
    set -x GOOGLE_ZONE (gcloud config get compute/zone 2>/dev/null)
    echo "TF env: $GOOGLE_PROJECT / $GOOGLE_REGION"
end
```

```bash
tf-env my-gcp-project   # switches gcloud + exports GOOGLE_* for terraform
terraform plan
```

#### Debug provider auth issues

```bash
TF_LOG=DEBUG terraform plan 2>&1 | grep -i "credential\|token\|auth\|quota"
```

#### Check what credentials Terraform will actually use

```bash
gcloud auth application-default print-access-token
# If this fails → terraform will also fail to auth
```

#### Enable required APIs before `terraform apply`

```bash
gcloud services enable compute.googleapis.com \
  container.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com
```

Or manage it in Terraform itself:

```hcl
resource "google_project_service" "apis" {
  for_each = toset([
    "compute.googleapis.com",
    "container.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}
```

## Tips

- Use `gcloud help <command>` for command-specific help
- Set defaults in config to avoid repeated flags
- Use `gcloud cheat-sheet` for quick reference
- Create multiple configurations for dev/staging/prod environments
- Always verify active project before running commands: `gcloud config list`
