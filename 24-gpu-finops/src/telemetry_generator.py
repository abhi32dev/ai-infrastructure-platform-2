"""Generates simulated GPU utilization telemetry with deliberately
realistic patterns: bursty training jobs (high utilization for a
stretch), followed by an idle gap (job finished, instance left running —
the actual real-world waste this project's cost engine exists to catch),
across multiple instances tagged to different teams.
"""

import random
from datetime import datetime, timedelta

from config import TELEMETRY_INTERVAL_MINUTES, SIMULATION_HOURS

INSTANCES = [
    {"instance_id": "gpu-001", "gpu_type": "A100", "team": "platform-ml"},
    {"instance_id": "gpu-002", "gpu_type": "A100", "team": "platform-ml"},
    {"instance_id": "gpu-003", "gpu_type": "H100", "team": "research"},
    {"instance_id": "gpu-004", "gpu_type": "L4", "team": "inference-serving"},
]


def generate_utilization_series(rng: random.Random, n_points: int, pattern: str) -> list[float]:
    """pattern: 'training' (mostly busy, few dips), 'idle_after_training'
    (busy first half, idle second half — the target waste pattern),
    'steady_serving' (moderate, consistent utilization)."""
    values = []
    for i in range(n_points):
        frac = i / n_points
        if pattern == "training":
            values.append(rng.uniform(70, 98))
        elif pattern == "idle_after_training":
            if frac < 0.4:
                values.append(rng.uniform(75, 97))
            else:
                values.append(rng.uniform(0, 8))  # job finished, instance left running idle
        elif pattern == "steady_serving":
            values.append(rng.uniform(35, 60))
    return values


def generate_telemetry(seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    n_points = int(SIMULATION_HOURS * 60 / TELEMETRY_INTERVAL_MINUTES)
    start_time = datetime(2026, 3, 1, 0, 0)

    patterns = ["training", "idle_after_training", "training", "steady_serving"]

    rows = []
    for instance, pattern in zip(INSTANCES, patterns):
        utilization_series = generate_utilization_series(rng, n_points, pattern)
        for i, util in enumerate(utilization_series):
            rows.append({
                "instance_id": instance["instance_id"],
                "gpu_type": instance["gpu_type"],
                "team": instance["team"],
                "timestamp": start_time + timedelta(minutes=i * TELEMETRY_INTERVAL_MINUTES),
                "utilization_pct": round(util, 1),
            })
    return rows


if __name__ == "__main__":
    rows = generate_telemetry()
    print(f"Generated {len(rows)} telemetry points across {len(INSTANCES)} instances "
          f"over {SIMULATION_HOURS}h at {TELEMETRY_INTERVAL_MINUTES}-min intervals.")
