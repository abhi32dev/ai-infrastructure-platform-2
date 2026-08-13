from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
MLFLOW_DB = Path(__file__).resolve().parent.parent / "mlflow.db"
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "mlartifacts"
BASELINE_FILE = Path(__file__).resolve().parent.parent / "baseline_metrics.json"

JUDGE_MODEL = "qwen2.5:1.5b"
JUDGE_TEMPERATURE = 0.0

# Which versioned prompt file is "current" — this is the one line you change
# to promote a new prompt version, and it's what MLflow logs as a run param.
CURRENT_PROMPT_VERSION = "v2"

MLFLOW_EXPERIMENT_NAME = "judge_prompt_eval"
REGRESSION_TOLERANCE = 0.0  # new agreement_rate must be >= baseline - tolerance
