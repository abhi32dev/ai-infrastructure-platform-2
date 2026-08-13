# Production Readiness — Terraform IaC Module

## Current state
Real Terraform module (S3, DynamoDB, SQS+DLQ) applied against LocalStack.
Found and fixed a real licensing-gate bug (LocalStack's `latest` tag now
requires a paid auth token). Verified all 3 resources' real usability via
boto3 write/read round-trips, not just `terraform apply` success. 5 tests
including a real-state regression guard on S3 versioning.

## Design decisions & trade-offs

| Decision | Why | Trade-off accepted |
|---|---|---|
| LocalStack, not real AWS | Free/local validation, same discipline as the resume's Moto-based testing | LocalStack's emulation isn't perfect — some AWS behaviors (IAM policy evaluation nuances, eventual consistency timing) don't fully match real AWS |
| Local Terraform state (no remote backend) | Appropriate for a single-developer local demo | Explicitly flagged: a real team needs remote state (S3 + DynamoDB locking) to avoid state conflicts between engineers |
| Same 3 resource types as projects 05/06 | Isolates "which IaC tool" as the comparison variable against those projects' Python-based provisioning | Doesn't demonstrate Terraform module composition, workspaces, or more complex multi-resource dependency graphs a real infra module would have |

## What's missing for real production use
- **Remote state backend** — explicitly documented as missing; needed
  the moment more than one person touches this infrastructure
- **Multi-environment workflow** — only a single `environment` variable,
  no `.tfvars` per environment or workspace separation; the resume's
  existing CDK "4-environment golden-path" bullet covers this via a
  different tool, not replicated here
- **Module composition/reusability** — this is a single flat `main.tf`,
  not broken into reusable modules the way a real infrastructure
  monorepo would organize shared resource patterns
- **CI/CD integration for Terraform itself** — no `terraform plan` review
  gate in a PR workflow (e.g., Atlantis, or a GitHub Actions plan/apply
  pipeline)

## Scaling considerations
- The resources themselves (S3, DynamoDB, SQS) scale independently of
  how they're provisioned — Terraform vs. CDK doesn't affect the
  underlying resource's runtime scaling characteristics
- A real multi-team organization scaling this pattern needs the module-
  composition and remote-state pieces above before it can be safely
  reused across many services

## Security & compliance considerations
- Uses fake `test`/`test` credentials pointed at LocalStack — obviously
  never acceptable against real AWS; a production Terraform setup needs
  proper credential management (assumed roles, not long-lived keys)
- No `tfsec`/`checkov` static security scanning integrated into this
  module's workflow — a production IaC pipeline should scan for common
  misconfigurations (public S3 buckets, overly permissive IAM) before
  apply

## Operational readiness
- No drift detection — nothing catches infrastructure that's been
  manually changed outside of Terraform after the fact
- No cost estimation (e.g., `terraform plan` + Infracost) integrated into
  the workflow before applying changes
