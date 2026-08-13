"""Honest scope note: this project has no real GPU cluster to monitor —
the telemetry is simulated (see telemetry_generator.py, with deliberately
realistic bursty-training + idle-gap patterns, clearly labeled as
synthetic). What's real and tested is the cost-governance ENGINE: idle
detection, per-team cost allocation, and threshold-based alerting — the
same 'the mechanism is real even though the input data is synthetic'
framing as project 07's seeded recommender A/B test.
"""

from pathlib import Path

# Illustrative on-demand GPU hourly rates (ballpark 2026 cloud pricing,
# not a specific provider's live rate card) — the point is the cost-
# governance logic, not precision-matching any one cloud's pricing page.
GPU_HOURLY_RATES = {
    "A100": 3.06,
    "H100": 4.98,
    "L4": 0.71,
}

IDLE_UTILIZATION_THRESHOLD_PCT = 15.0   # below this = considered idle
IDLE_SUSTAINED_MINUTES = 30              # must stay idle this long to count as "wasted," not just a dip
ALERT_IDLE_COST_THRESHOLD_USD = 5.0      # per-instance idle spend that triggers an alert

TELEMETRY_INTERVAL_MINUTES = 5
SIMULATION_HOURS = 6

LEDGER_DB = Path(__file__).resolve().parent.parent / "gpu_cost_ledger.sqlite"
DASHBOARD_HTML = Path(__file__).resolve().parent.parent / "gpu_dashboard.html"
