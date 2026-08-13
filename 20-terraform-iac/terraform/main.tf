terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Points the AWS provider at LocalStack instead of real AWS — same
# "validate infra code entirely offline pre-deployment using LocalStack
# to emulate AWS services rather than testing against live cloud
# resources" pattern already on the resume, applied to Terraform instead
# of the Moto-based Python testing used there.
provider "aws" {
  region                      = "us-west-2"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    s3       = "http://localhost:4566"
    dynamodb = "http://localhost:4566"
    sqs      = "http://localhost:4566"
  }
}

variable "environment" {
  description = "Deployment environment name, used as a resource-naming prefix — mirrors the resume's 4-environment golden-path CDK pattern"
  type        = string
  default     = "dev"
}

# S3 bucket for batch checkpoints — the same durable-checkpoint pattern
# as project 05's agent runtime and the resume's S3-manifest-ingestion bullet
resource "aws_s3_bucket" "checkpoints" {
  bucket = "aegis-${var.environment}-checkpoints"
}

resource "aws_s3_bucket_versioning" "checkpoints_versioning" {
  bucket = aws_s3_bucket.checkpoints.id
  versioning_configuration {
    status = "Enabled"
  }
}

# DynamoDB table for TTL-keyed idempotency markers — the same dedup
# pattern as project 05's idempotency store and the resume's "TTL-Based
# Idempotency" bullet, provisioned as real infrastructure-as-code instead
# of a local JSON file
resource "aws_dynamodb_table" "idempotency" {
  name         = "aegis-${var.environment}-idempotency"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "idempotency_key"

  attribute {
    name = "idempotency_key"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

# SQS queue for backpressure-isolated ingestion — the Terraform
# equivalent of project 06's Redis-backed queue, matching the resume's
# actual production choice (SQS) rather than the local Redis substitute
resource "aws_sqs_queue" "ingestion_dlq" {
  name                      = "aegis-${var.environment}-ingestion-dlq"
  message_retention_seconds = 1209600 # 14 days
}

resource "aws_sqs_queue" "ingestion" {
  name                       = "aegis-${var.environment}-ingestion"
  visibility_timeout_seconds = 30

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ingestion_dlq.arn
    maxReceiveCount      = 3
  })
}

output "bucket_name" {
  value = aws_s3_bucket.checkpoints.bucket
}

output "table_name" {
  value = aws_dynamodb_table.idempotency.name
}

output "queue_url" {
  value = aws_sqs_queue.ingestion.url
}

output "dlq_url" {
  value = aws_sqs_queue.ingestion_dlq.url
}
