"""Test categories:
1. Positive/negative gate AND-logic — deterministic, stubbed models.
2. Fail-safe behavior on malformed model output (negative/edge case).
3. Regression guard — every gate decision is appended to the audit log.
4. Live integration test against the real local models.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import gate
import generator
import judge


def test_gate_blocks_when_judge_rejects_even_if_generator_approves():
    with patch("gate.propose", return_value={"decision": "APPROVE", "rationale": "r"}), \
         patch("gate.review", return_value={"verdict": "REJECT", "reasoning": "r"}):
        result = gate.run_gate({"id": "t1", "situation": "x", "proposed_action": "a", "expected_safe": False})
    assert result["gate_approved"] is False
    assert "BLOCKED" in result["execution_result"]


def test_gate_blocks_when_generator_rejects_even_if_judge_approves():
    with patch("gate.propose", return_value={"decision": "REJECT", "rationale": "r"}), \
         patch("gate.review", return_value={"verdict": "APPROVE", "reasoning": "r"}):
        result = gate.run_gate({"id": "t2", "situation": "x", "proposed_action": "a", "expected_safe": False})
    assert result["gate_approved"] is False


def test_gate_approves_only_when_both_approve():
    with patch("gate.propose", return_value={"decision": "APPROVE", "rationale": "r"}), \
         patch("gate.review", return_value={"verdict": "APPROVE", "reasoning": "r"}):
        result = gate.run_gate({"id": "t3", "situation": "x", "proposed_action": "a", "expected_safe": True})
    assert result["gate_approved"] is True
    assert "SIMULATED EXECUTION" in result["execution_result"]


def test_live_gate_blocks_destructive_action():
    """Integration test against real local models — the one scenario every
    small model consistently gets right in practice."""
    from scenarios import SCENARIOS

    destructive = next(s for s in SCENARIOS if s["id"] == "s3")
    result = gate.run_gate(destructive)
    assert result["gate_approved"] is False


# --- Negative / edge cases: malformed model output ---

def test_generator_fails_safe_to_reject_on_unparsable_json():
    class FakeResponse:
        content = "not valid json at all"

    with patch("generator.ChatOllama") as mock_llm:
        mock_llm.return_value.invoke.return_value = FakeResponse()
        result = generator.propose("some situation", "some_action")
    assert result["decision"] == "REJECT"
    assert "unparsable" in result["rationale"]


def test_judge_fails_safe_to_reject_on_unparsable_json():
    class FakeResponse:
        content = "{broken json"

    with patch("judge.ChatOllama") as mock_llm:
        mock_llm.return_value.invoke.return_value = FakeResponse()
        result = judge.review("some situation", "some_action")
    assert result["verdict"] == "REJECT"
    assert "unparsable" in result["reasoning"]


def test_gate_blocks_when_both_models_reject():
    with patch("gate.propose", return_value={"decision": "REJECT", "rationale": "r"}), \
         patch("gate.review", return_value={"verdict": "REJECT", "reasoning": "r"}):
        result = gate.run_gate({"id": "t4", "situation": "x", "proposed_action": "a", "expected_safe": False})
    assert result["gate_approved"] is False


# --- Regression guard ---

def test_every_gate_decision_is_appended_to_audit_log():
    from config import AUDIT_LOG

    log_lines_before = AUDIT_LOG.read_text().count("\n") if AUDIT_LOG.exists() else 0

    with patch("gate.propose", return_value={"decision": "APPROVE", "rationale": "r"}), \
         patch("gate.review", return_value={"verdict": "APPROVE", "reasoning": "r"}):
        gate.run_gate({"id": "audit-check", "situation": "x", "proposed_action": "a", "expected_safe": True})

    log_lines_after = AUDIT_LOG.read_text().count("\n")
    assert log_lines_after == log_lines_before + 1

    last_line = json.loads(AUDIT_LOG.read_text().strip().split("\n")[-1])
    assert last_line["scenario_id"] == "audit-check"
