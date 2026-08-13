from pathlib import Path

GEN_MODEL = "llama3.2:1b"     # proposes the automation decision
JUDGE_MODEL = "qwen2.5:1.5b"  # independent second model that verifies it
GEN_TEMPERATURE = 0.2
JUDGE_TEMPERATURE = 0.0        # judge should be as deterministic as possible

AUDIT_LOG = Path(__file__).resolve().parent.parent / "logs" / "audit.jsonl"
