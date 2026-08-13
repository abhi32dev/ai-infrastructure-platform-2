# 20 — Terraform IaC Module

A real Terraform module (`hashicorp/aws` provider, pointed at LocalStack
instead of real AWS) provisioning the exact three resource types this
portfolio's projects already model conceptually — S3 checkpoints (project
05), DynamoDB idempotency markers (project 05), SQS backpressure queues
with a dead-letter redrive policy (project 06) — as real, applied
infrastructure-as-code, verified usable with real write/read round-trips
through `boto3`, not just "terraform apply succeeded."

## Maps to the market-gap research
- Terraform named in nearly every ML platform engineering posting
  searched; the resume's existing IaC story is **AWS CDK only** — this
  project demonstrates a second IaC tool, the same underlying AWS
  resource model expressed a different way

## Setup

```bash
cd 20-terraform-iac
docker compose up -d          # LocalStack (community edition, pinned — see finding below)

cd terraform
terraform init
terraform apply -auto-approve

cd ..
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python verify_resources.py    # real write/read round-trip against every resource
```

## A real licensing-gate bug hit and fixed

`docker-compose.yml` originally pinned `localstack/localstack:latest`.
That image now **requires a paid `LOCALSTACK_AUTH_TOKEN`** and exits
immediately with `License activation failed!` if one isn't set —
LocalStack's `latest` tag has shifted toward gating more behind a
license check. **Fix**: pinned to `localstack/localstack:3.8.1`, a
known community-edition version, confirmed via
`curl localhost:4566/_localstack/health` showing `"edition": "community"`
and `s3`/`dynamodb`/`sqs` all `"available"` with no auth token set.
Same "verify the free tier claim directly, don't assume the docs/tag
still describe current behavior" discipline as project 18's
`bitsandbytes` finding — this time in the opposite direction (a
previously-free thing quietly became gated).

## What's provisioned

| Resource | Mirrors | Purpose |
|---|---|---|
| `aws_s3_bucket.checkpoints` (+ versioning) | Project 05's checkpoint pattern | Durable batch/agent checkpoints |
| `aws_dynamodb_table.idempotency` (TTL-enabled) | Project 05's idempotency store | TTL-keyed dedup markers |
| `aws_sqs_queue.ingestion` + `.ingestion_dlq` | Project 06's Redis queue | Backpressure-isolated ingestion with a 3-attempt redrive-to-DLQ policy |

## Verified results (this run)

```
terraform apply: 5 resources added, 0 changed, 0 destroyed

  [OK] s3: real write+read round-trip succeeded
  [OK] dynamodb: real write+read round-trip succeeded
  [OK] sqs: real write+read round-trip succeeded
```

Every resource was verified with an actual write followed by an actual
read — a real object stored and retrieved from S3, a real item put and
fetched from DynamoDB, a real message sent and received through SQS —
not just a green `terraform apply`, which only proves the API call to
*create* something succeeded.

## Tests

```bash
cd 20-terraform-iac && source .venv/bin/activate && pytest -q
```
5 tests, reading real resource identifiers from `terraform output -json`
(never hardcoded — a naming-convention change in `main.tf` would surface
as a clear test failure, not a silent mismatch): S3/DynamoDB/SQS
read-write round-trips, a negative check that the DLQ and main queue are
genuinely distinct resources (a copy-paste bug could silently point both
at the same queue), and a regression guard reading the actual applied
Terraform state to confirm S3 versioning is really `Enabled`, not just
declared in the `.tf` file.

## Teardown

```bash
cd terraform && terraform destroy -auto-approve
cd .. && docker compose down
```

## What to say in an interview

- **Why point Terraform at LocalStack instead of documenting "would work
  against real AWS"?** Because a plan that only exists as unapplied HCL
  proves the syntax is valid, not that the resources, their
  interdependencies (the DLQ's ARN feeding the main queue's redrive
  policy), or the provider configuration actually work. `terraform apply`
  against LocalStack is the same free/local validation discipline as the
  resume's Moto-based Python testing, applied one layer up the stack.
- **Why the same three resource types already modeled in projects 05/06
  instead of something new?** To make the IaC-tool comparison direct and
  honest: the same infrastructure, expressed once conceptually in
  project 05/06's Python code and once as real Terraform HCL, isolates
  "which IaC tool" as the only variable — exactly the kind of side-by-side
  a Staff-level interview question about IaC choices would probe.
- **Why verify with boto3 instead of trusting `terraform apply`'s
  success output?** Because LocalStack (and real AWS) can report a
  resource as successfully created while it's still not genuinely usable
  in the way the application expects — e.g., versioning not actually
  enabled, wrong region, an ARN reference that resolved to the wrong
  resource. Applying, then separately using each resource for its real
  purpose, is the only way to prove the infrastructure does what it's
  for, not just that it exists.
- **Known limitation to volunteer:** this module has no remote state
  backend (state lives in a local `.tfstate` file) and no
  environment-specific `.tfvars` files beyond the single `environment`
  variable — appropriate for a local demo, but a production Terraform
  setup needs remote state (S3 + DynamoDB locking, ironically the same
  two resource types this module provisions) and a proper multi-
  environment workflow, which the resume's existing CDK "4-environment
  golden-path template" bullet already covers via a different tool.
