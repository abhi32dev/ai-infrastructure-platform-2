"""The real, tested part of this project: given a telemetry stream,
computes per-instance total cost, detects sustained idle windows (not
momentary dips — a single low reading shouldn't trigger an alert, only
a SUSTAINED idle period, matching how a real FinOps system avoids
alert fatigue on noise), allocates cost by team, and raises alerts when
idle spend crosses a threshold.
"""

from collections import defaultdict

from config import (
    GPU_HOURLY_RATES, IDLE_UTILIZATION_THRESHOLD_PCT, IDLE_SUSTAINED_MINUTES,
    ALERT_IDLE_COST_THRESHOLD_USD, TELEMETRY_INTERVAL_MINUTES,
)

POINTS_PER_HOUR = 60 / TELEMETRY_INTERVAL_MINUTES
SUSTAINED_IDLE_POINTS = int(IDLE_SUSTAINED_MINUTES / TELEMETRY_INTERVAL_MINUTES)


def cost_per_point(gpu_type: str) -> float:
    hourly_rate = GPU_HOURLY_RATES[gpu_type]
    return hourly_rate / POINTS_PER_HOUR


def find_sustained_idle_windows(points: list[dict]) -> list[list[dict]]:
    """A telemetry point counts toward a 'wasted' window only if it's
    part of a RUN of at least SUSTAINED_IDLE_POINTS consecutive
    below-threshold readings — a momentary dip during real training
    (e.g. between batches) must not be flagged as waste."""
    windows = []
    current_run = []

    for point in points:
        if point["utilization_pct"] < IDLE_UTILIZATION_THRESHOLD_PCT:
            current_run.append(point)
        else:
            if len(current_run) >= SUSTAINED_IDLE_POINTS:
                windows.append(current_run)
            current_run = []

    if len(current_run) >= SUSTAINED_IDLE_POINTS:
        windows.append(current_run)

    return windows


def analyze_instance(instance_id: str, points: list[dict]) -> dict:
    gpu_type = points[0]["gpu_type"]
    team = points[0]["team"]
    per_point_cost = cost_per_point(gpu_type)

    total_cost = len(points) * per_point_cost

    idle_windows = find_sustained_idle_windows(points)
    idle_points = sum(len(w) for w in idle_windows)
    idle_cost = idle_points * per_point_cost

    return {
        "instance_id": instance_id,
        "gpu_type": gpu_type,
        "team": team,
        "total_cost_usd": round(total_cost, 2),
        "idle_cost_usd": round(idle_cost, 2),
        "idle_windows_count": len(idle_windows),
        "idle_pct_of_runtime": round(idle_points / len(points) * 100, 1) if points else 0,
        "alert": idle_cost >= ALERT_IDLE_COST_THRESHOLD_USD,
    }


def run_analysis(telemetry: list[dict]) -> dict:
    by_instance = defaultdict(list)
    for row in telemetry:
        by_instance[row["instance_id"]].append(row)

    instance_reports = [analyze_instance(iid, points) for iid, points in by_instance.items()]

    by_team = defaultdict(lambda: {"total_cost_usd": 0.0, "idle_cost_usd": 0.0})
    for report in instance_reports:
        by_team[report["team"]]["total_cost_usd"] += report["total_cost_usd"]
        by_team[report["team"]]["idle_cost_usd"] += report["idle_cost_usd"]

    total_cost = sum(r["total_cost_usd"] for r in instance_reports)
    total_idle_cost = sum(r["idle_cost_usd"] for r in instance_reports)

    return {
        "instances": instance_reports,
        "by_team": dict(by_team),
        "total_cost_usd": round(total_cost, 2),
        "total_idle_cost_usd": round(total_idle_cost, 2),
        "idle_pct_of_total_spend": round(total_idle_cost / total_cost * 100, 1) if total_cost else 0,
        "alerts": [r for r in instance_reports if r["alert"]],
    }


if __name__ == "__main__":
    from telemetry_generator import generate_telemetry

    telemetry = generate_telemetry()
    result = run_analysis(telemetry)

    print(f"Total spend: ${result['total_cost_usd']}")
    print(f"Total idle (wasted) spend: ${result['total_idle_cost_usd']} "
          f"({result['idle_pct_of_total_spend']}% of total)")

    print("\nPer-instance:")
    for r in result["instances"]:
        flag = " [ALERT]" if r["alert"] else ""
        print(f"  {r['instance_id']} ({r['gpu_type']}, {r['team']}): "
              f"total=${r['total_cost_usd']} idle=${r['idle_cost_usd']} "
              f"({r['idle_pct_of_runtime']}% idle){flag}")

    print("\nPer-team:")
    for team, costs in result["by_team"].items():
        print(f"  {team}: total=${costs['total_cost_usd']:.2f} idle=${costs['idle_cost_usd']:.2f}")
