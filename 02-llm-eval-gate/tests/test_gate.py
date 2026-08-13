"""Two layers of test:
1. Deterministic unit tests of the gate's AND-logic using stubbed models
   (no Ollama needed, no flakiness).
2. A live integration test against the real models, tolerant of the known
   false-reject case, to prove the wiring actually works end to end.
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import gate


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
