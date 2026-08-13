"""Live integration tests against the REAL kind cluster (no mocking, no
simulation) — requires the cluster to already be up and the Deployment
applied (see README setup steps). These tests drive kubectl directly and
assert on real cluster state.
"""

import json
import subprocess
import time

import pytest


def kubectl(*args) -> str:
    result = subprocess.run(["kubectl", *args], capture_output=True, text=True, timeout=30)
    return result.stdout.strip()


def get_pod_names():
    out = kubectl("get", "pods", "-l", "app=model-serving", "-o", "name")
    return [line.split("/")[1] for line in out.splitlines() if line]


def get_ready_pods():
    out = kubectl("get", "pods", "-o", "jsonpath={range .items[*]}{.metadata.name}\t{.status.containerStatuses[0].ready}\n{end}")
    ready = {}
    for line in out.splitlines():
        name, is_ready = line.split("\t")
        ready[name] = is_ready == "true"
    return ready


def get_service_endpoints():
    out = kubectl("get", "endpoints", "model-serving", "-o", "jsonpath={.subsets[*].addresses[*].ip}")
    return out.split() if out else []


@pytest.fixture(scope="module", autouse=True)
def require_cluster():
    out = kubectl("get", "deployment", "model-serving")
    if not out:
        pytest.skip("kind cluster / model-serving deployment not running — see README setup")


def test_deployment_has_two_ready_replicas():
    ready = get_ready_pods()
    assert len(ready) == 2
    assert all(ready.values())


def test_service_has_endpoints_for_all_ready_pods():
    endpoints = get_service_endpoints()
    assert len(endpoints) == 2


def test_hpa_is_configured_with_correct_bounds():
    out = kubectl("get", "hpa", "model-serving-hpa", "-o", "json")
    hpa = json.loads(out)
    assert hpa["spec"]["minReplicas"] == 2
    assert hpa["spec"]["maxReplicas"] == 6
    assert hpa["spec"]["metrics"][0]["resource"]["target"]["averageUtilization"] == 60


def test_all_pods_currently_report_healthy_200():
    """Cluster-level sanity check on the live deployment (does not touch
    Ollama — safe to run repeatedly as part of CI)."""
    pods = get_pod_names()
    assert len(pods) == 2
    check_script = (
        "import urllib.request\n"
        "r = urllib.request.urlopen('http://localhost:8000/health', timeout=5)\n"
        "print(r.status)\n"
    )
    for pod in pods:
        status = subprocess.run(
            ["kubectl", "exec", pod, "--", "python3", "-c", check_script],
            capture_output=True, text=True, timeout=15,
        ).stdout.strip()
        assert status == "200"
