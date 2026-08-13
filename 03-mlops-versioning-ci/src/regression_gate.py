"""CI entry point: runs the eval harness against the CURRENT_PROMPT_VERSION,
compares its agreement_rate against a committed baseline, and exits non-zero
if it regressed — this is what GitHub Actions calls on every PR touching
prompt/automation logic (the resume's 'CI-Gated Automation Changes' bullet).

Usage:
  python regression_gate.py                 # check current version against baseline, exit 1 on regression
  python regression_gate.py --update-baseline  # (re)write the baseline after an intentional, reviewed change
"""

import json
import sys

from config import BASELINE_FILE, REGRESSION_TOLERANCE, CURRENT_PROMPT_VERSION
from eval_harness import evaluate_and_log


def load_baseline() -> dict | None:
    if not BASELINE_FILE.exists():
        return None
    return json.loads(BASELINE_FILE.read_text())


def write_baseline(summary: dict):
    baseline = {
        "prompt_version": summary["prompt_version"],
        "agreement_rate": summary["agreement_rate"],
        "avg_latency_sec": summary["avg_latency_sec"],
    }
    BASELINE_FILE.write_text(json.dumps(baseline, indent=2))


def main():
    update = "--update-baseline" in sys.argv

    summary = evaluate_and_log(CURRENT_PROMPT_VERSION)
    print(f"Current run: prompt_version={summary['prompt_version']} "
          f"agreement_rate={summary['agreement_rate']:.2f}")

    if update:
        write_baseline(summary)
        print(f"Baseline updated and committed to {BASELINE_FILE}")
        return 0

    baseline = load_baseline()
    if baseline is None:
        print("No baseline found — treating this run as the first baseline.")
        write_baseline(summary)
        return 0

    print(f"Baseline:    prompt_version={baseline['prompt_version']} "
          f"agreement_rate={baseline['agreement_rate']:.2f}")

    threshold = baseline["agreement_rate"] - REGRESSION_TOLERANCE
    if summary["agreement_rate"] < threshold:
        print(
            f"\nREGRESSION DETECTED: agreement_rate {summary['agreement_rate']:.2f} "
            f"< baseline {baseline['agreement_rate']:.2f} (tolerance {REGRESSION_TOLERANCE}). "
            f"Blocking merge."
        )
        return 1

    print("\nNo regression. Gate passes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
