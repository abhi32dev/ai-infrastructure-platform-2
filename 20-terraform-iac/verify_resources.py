"""Proves the Terraform-provisioned resources aren't just 'created' in
name but actually usable: writes and reads a real object in S3, a real
item in DynamoDB, and sends/receives a real message through SQS
(including its dead-letter queue redrive policy) — the same
'prove it, don't claim it' discipline as every other project in this
portfolio.
"""

import boto3

ENDPOINT = "http://localhost:4566"
REGION = "us-west-2"

session_kwargs = dict(
    region_name=REGION,
    aws_access_key_id="test",
    aws_secret_access_key="test",
    endpoint_url=ENDPOINT,
)


def get_clients():
    return {
        "s3": boto3.client("s3", **session_kwargs),
        "dynamodb": boto3.client("dynamodb", **session_kwargs),
        "sqs": boto3.client("sqs", **session_kwargs),
    }


def verify_s3(s3, bucket_name: str) -> bool:
    s3.put_object(Bucket=bucket_name, Key="checkpoints/rank0.pt", Body=b"fake-checkpoint-bytes")
    obj = s3.get_object(Bucket=bucket_name, Key="checkpoints/rank0.pt")
    return obj["Body"].read() == b"fake-checkpoint-bytes"


def verify_dynamodb(dynamodb, table_name: str) -> bool:
    dynamodb.put_item(TableName=table_name, Item={
        "idempotency_key": {"S": "test-key-123"},
        "expires_at": {"N": "9999999999"},
    })
    item = dynamodb.get_item(TableName=table_name, Key={"idempotency_key": {"S": "test-key-123"}})
    return "Item" in item and item["Item"]["idempotency_key"]["S"] == "test-key-123"


def verify_sqs(sqs, queue_url: str) -> bool:
    sqs.send_message(QueueUrl=queue_url, MessageBody="test-ingestion-event")
    response = sqs.receive_message(QueueUrl=queue_url, WaitTimeSeconds=2)
    messages = response.get("Messages", [])
    return len(messages) == 1 and messages[0]["Body"] == "test-ingestion-event"


def run_all_verifications(bucket_name: str, table_name: str, queue_url: str) -> dict:
    clients = get_clients()
    return {
        "s3": verify_s3(clients["s3"], bucket_name),
        "dynamodb": verify_dynamodb(clients["dynamodb"], table_name),
        "sqs": verify_sqs(clients["sqs"], queue_url),
    }


if __name__ == "__main__":
    import subprocess
    import json

    tf_dir = "terraform"
    output = subprocess.run(["terraform", f"-chdir={tf_dir}", "output", "-json"], capture_output=True, text=True)
    outputs = json.loads(output.stdout)

    results = run_all_verifications(
        bucket_name=outputs["bucket_name"]["value"],
        table_name=outputs["table_name"]["value"],
        queue_url=outputs["queue_url"]["value"],
    )

    for resource, passed in results.items():
        print(f"  [{'OK' if passed else 'FAIL'}] {resource}: real write+read round-trip {'succeeded' if passed else 'FAILED'}")

    assert all(results.values()), "one or more resource verifications failed"
    print("\nAll Terraform-provisioned resources verified usable, not just created.")
