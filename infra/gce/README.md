# First MAS-Core pilot deployment target

Owner delegated hosting selection and will perform the release review. Proposed
target: one Google Compute Engine Debian 12 VM in Johannesburg, 4 vCPU / 16 GiB,
30 GiB boot disk and a separate 100 GiB persistent state disk. Firebase Hosting
alone cannot run Docker workers or preserve these SQLite stores. Cloud Run is
not selected for the current Docker-worker/state architecture. Firebase can
later host an independently qualified public frontend.

## Scope and access

This is a reviewable infrastructure candidate, not a deployed or production-
approved service. Only IAP SSH ingress is allowed. The staged dashboard binds
to VM loopback; access uses an authenticated SSH tunnel. No public application
port, Docker socket mount, automatic dispatch or service account project role
is configured. Candidate workers must continue using their own no-egress,
no-host-mount Docker policy. The default runtime container can refuse nested
bubblewrap execution; trusted coding coordination belongs on the dedicated host,
not a dashboard socket mount or weakened sandbox.

The data disk is protected from Terraform deletion and the VM has deletion
protection. The startup script formats only a fresh signature-free data disk,
refuses other filesystems and does not silently continue on mount failure.
It installs a disabled staged service template. It does not initialize actual
tenants, retrieve credentials, enable a service or authorize production.

## Before a cloud plan

Supply the actual Google Cloud project ID associated with the Firebase project
if appropriate. Confirm billing, organization policy, region/machine availability,
and Compute Engine/IAM/IAP/OS Login permissions. Firebase access alone proves
none of those permissions. Authenticate using the operator's approved Cloud CLI
or workload identity route; never place credentials in this repository.

```sh
cd infra/gce
cp terraform.tfvars.example terraform.tfvars
# Edit project_id, then run with authorized Google Cloud credentials:
terraform init
terraform plan -out=pilot.tfplan
terraform show pilot.tfplan
```

Review resources, IAM identity, firewall, disks and deletion protections in that
saved plan. The Debian family resolves to an exact image during authenticated
planning or provisioning; record that identity for deployment qualification.
Do not apply until
the owner approves the plan and regional cost estimate. No Terraform apply is
performed by preparation or local validation.

Costs to price: e2-standard-4 compute hours, 130 GiB balanced persistent disks,
external IPv4, outbound traffic and any separately added backups. Region-specific
prices, taxes and currency must come from the actual project/billing context;
no monthly total is asserted here. Review using the Google Cloud pricing
calculator: https://cloud.google.com/products/calculator

## After infrastructure and release approval

Transfer the reviewed runtime image by an authorized registry or IAP SCP, verify
its recorded digest, and load it. Keep runtime-image configuration in root-only
`/etc/mas-core/runtime.env` with `MAS_RUNTIME_IMAGE=sha256:<verified local image ID>`.
Never put provider keys in Terraform metadata, image layers, CLI arguments or
dashboard container environment. Secure trusted coordinator/IAM configuration is
a separate admission step. No initial admin password or default credential exists.

Only after applicable release checks and owner approval, the operator can enable
`mas-core-dashboard.service`. For a private operator tunnel:

```sh
gcloud compute ssh mas-core-pilot --project ACTUAL_PROJECT_ID \
  --zone africa-south1-a --tunnel-through-iap -- -N -L 8080:127.0.0.1:8080
```

Required grants for the actual human operator include appropriate OS Login and
IAP tunnel access; this template intentionally does not invent a user identity
or grant project-wide roles. Verify health, unauthenticated mutation denial,
identity-bound workflows and storage persistence. Do not interpret an active
health endpoint as production acceptance.

## Remaining release requirements

Independent witness administration/storage/restore separation, historical identity
migration, integrated PM funding/scheduling/approval/export, measured operational
capacity and final review remain open. A second VM managed by the same authority
does not by itself establish an independently administered witness. No sustained
availability, load, disaster-recovery RPO/RTO or broad model-quality target has
been passed by preparing this infrastructure.
