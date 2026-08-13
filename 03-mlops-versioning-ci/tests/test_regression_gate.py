"""Deterministic tests of the gate's comparison logic (mocked eval results,
no Ollama needed) plus one live test proving v1 -> v2 is a measured,
reproducible improvement, not a one-off.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import regression_gate


def test_no_baseline_file_creates_one_and_passes(tmp_path, monkeypatch):
    fake_baseline = tmp_path / "baseline_metrics.json"
    monkeypatch.setattr(regression_gate, "BASELINE_FILE", fake_baseline)
    with patch("regression_gate.evaluate_and_log", return_value={"prompt_version": "v2", "agreement_rate": 0.83, "avg_latency_sec": 0.5}):
        with patch.object(sys, "argv", ["regression_gate.py"]):
            code = regression_gate.main()
    assert code == 0
    assert fake_baseline.exists()
    assert json.loads(fake_baseline.read_text())["agreement_rate"] == 0.83


def test_regression_blocks(tmp_path, monkeypatch):
    fake_baseline = tmp_path / "baseline_metrics.json"
    fake_baseline.write_text(json.dumps({"prompt_version": "v2", "agreement_rate": 0.83, "avg_latency_sec": 0.5}))
    monkeypatch.setattr(regression_gate, "BASELINE_FILE", fake_baseline)
    with patch("regression_gate.evaluate_and_log", return_value={"prompt_version": "v1", "agreement_rate": 0.33, "avg_latency_sec": 0.7}):
        with patch.object(sys, "argv", ["regression_gate.py"]):
            code = regression_gate.main()
    assert code == 1


def test_equal_or_better_passes(tmp_path, monkeypatch):
    fake_baseline = tmp_path / "baseline_metrics.json"
    fake_baseline.write_text(json.dumps({"prompt_version": "v2", "agreement_rate": 0.83, "avg_latency_sec": 0.5}))
    monkeypatch.setattr(regression_gate, "BASELINE_FILE", fake_baseline)
    with patch("regression_gate.evaluate_and_log", return_value={"prompt_version": "v2b", "agreement_rate": 0.83, "avg_latency_sec": 0.4}):
        with patch.object(sys, "argv", ["regression_gate.py"]):
            code = regression_gate.main()
    assert code == 0


def test_live_v1_vs_v2_agreement_rate_gap():
    """Integration test: proves the v1 -> v2 prompt improvement is real,
    not a one-off from the demo run."""
    from eval_harness import evaluate

    v1 = evaluate("v1")
    v2 = evaluate("v2")
    assert v2["agreement_rate"] > v1["agreement_rate"]
