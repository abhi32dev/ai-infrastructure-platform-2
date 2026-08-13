"""The gate itself: an action only actually executes (simulated here) if
BOTH the generator proposes APPROVE and the independent judge also
verdicts APPROVE. Every decision is written to an append-only audit log,
mirroring the CONDOR pattern of a reproducible history for every automation
decision (the resume's MLflow version-tracking bullet — project 03 adds the
MLflow layer on top of this gate).
"""

import json
import time
from pathlib import Path

from config import AUDIT_LOG
from generator import propose
from judge import review


def execute_action(action: str, situation: str) -> str:
    """Stand-in for actually calling AWS/K8s/etc. Never called unless the
    gate approves."""
    return f"[SIMULATED EXECUTION] action='{action}' taken for situation: {situation[:60]}..."


def run_gate(scenario: dict) -> dict:
    situation = scenario["situation"]
    action = scenario["proposed_action"]

    gen_result = propose(situation, action)
    judge_result = review(situation, action)

    gen_approved = gen_result.get("decision") == "APPROVE"
    judge_approved = judge_result.get("verdict") == "APPROVE"
    gate_approved = gen_approved and judge_approved

    outcome = {
        "scenario_id": scenario["id"],
        "action": action,
        "generator_decision": gen_result.get("decision"),
        "generator_rationale": gen_result.get("rationale"),
        "judge_verdict": judge_result.get("verdict"),
        "judge_reasoning": judge_result.get("reasoning"),
        "gate_approved": gate_approved,
        "expected_safe": scenario.get("expected_safe"),
        "agrees_with_expected": gate_approved == scenario.get("expected_safe"),
        "timestamp": time.time(),
    }

    if gate_approved:
        outcome["execution_result"] = execute_action(action, situation)
    else:
        outcome["execution_result"] = "BLOCKED — did not reach production"

    _append_audit(outcome)
    return outcome


def _append_audit(outcome: dict):
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(outcome) + "\n")


if __name__ == "__main__":
    from scenarios import SCENARIOS

    agree = 0
    for sc in SCENARIOS:
        result = run_gate(sc)
        agree += result["agrees_with_expected"]
        flag = "OK " if result["agrees_with_expected"] else "MISMATCH"
        print(
            f"[{flag}] {result['scenario_id']}: action={result['action']} "
            f"gen={result['generator_decision']} judge={result['judge_verdict']} "
            f"-> gate={'APPROVE' if result['gate_approved'] else 'BLOCK'} "
            f"(expected_safe={result['expected_safe']})"
        )
    print(f"\nAgreement with human-labeled expectation: {agree}/{len(SCENARIOS)}")
    print(f"Audit log: {AUDIT_LOG}")
