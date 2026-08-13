"""Live tests against the real Terraform-provisioned LocalStack resources
— no mocking. Requires `terraform apply` to have already run (see
README); reads the actual resource identifiers from `terraform output`
rather than hardcoding names, so the tests fail loudly if the module's
naming convention ever changes.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from verify_resources import get_clients, verify_s3, verify_dynamodb, verify_sqs

TF_DIR = Path(__file__).resolve().parent.parent / "terraform"


@pytest.fixture(scope="module")
def tf_outputs():
    result = subprocess.run(
        ["terraform", f"-chdir={TF_DIR}", "output", "-json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        pytest.skip("terraform apply has not been run — see README setup steps")
    return json.loads(result.stdout)


def test_s3_bucket_is_writable_and_readable(tf_outputs):
    clients = get_clients()
    assert verify_s3(clients["s3"], tf_outputs["bucket_name"]["value"]) is True


def test_dynamodb_table_is_writable_and_readable(tf_outputs):
    clients = get_clients()
    assert verify_dynamodb(clients["dynamodb"], tf_outputs["table_name"]["value"]) is True


def test_sqs_queue_is_writable_and_readable(tf_outputs):
    clients = get_clients()
    assert verify_sqs(clients["sqs"], tf_outputs["queue_url"]["value"]) is True


def test_dlq_is_a_distinct_queue_from_the_main_queue(tf_outputs):
    """Negative/regression guard: the DLQ and main queue must be
    different resources with different URLs — a copy-paste bug in the
    Terraform config could accidentally point both outputs at the same
    queue, silently breaking the redrive-on-failure pattern."""
    assert tf_outputs["queue_url"]["value"] != tf_outputs["dlq_url"]["value"]


def test_s3_bucket_versioning_is_enabled():
    """Regression guard on a specific resource attribute, not just
    existence: versioning must actually be enabled on the checkpoints
    bucket, matching the durable-checkpoint requirement it exists for."""
    result = subprocess.run(
        ["terraform", f"-chdir={TF_DIR}", "show", "-json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        pytest.skip("terraform apply has not been run — see README setup steps")
    state = json.loads(result.stdout)
    resources = state["values"]["root_module"]["resources"]
    versioning = next(r for r in resources if r["type"] == "aws_s3_bucket_versioning")
    assert versioning["values"]["versioning_configuration"][0]["status"] == "Enabled"
