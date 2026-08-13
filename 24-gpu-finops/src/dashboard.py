"""Self-contained HTML dashboard, same plain-HTML/CSS pattern as project
14's cost dashboard — no charting library, no build step, opens directly
in a browser.
"""

from config import DASHBOARD_HTML
from telemetry_generator import generate_telemetry
from cost_engine import run_analysis


def generate_dashboard():
    telemetry = generate_telemetry()
    result = run_analysis(telemetry)

    instance_rows = ""
    for r in result["instances"]:
        alert_badge = '<span style="color:#C23B2E;font-weight:700">ALERT</span>' if r["alert"] else '<span style="color:#1F8F63">ok</span>'
        instance_rows += (
            f"<tr><td>{r['instance_id']}</td><td>{r['gpu_type']}</td><td>{r['team']}</td>"
            f"<td>${r['total_cost_usd']:.2f}</td><td>${r['idle_cost_usd']:.2f}</td>"
            f"<td>{r['idle_pct_of_runtime']}%</td><td>{alert_badge}</td></tr>\n"
        )

    team_rows = ""
    for team, costs in result["by_team"].items():
        team_rows += (
            f"<tr><td>{team}</td><td>${costs['total_cost_usd']:.2f}</td>"
            f"<td>${costs['idle_cost_usd']:.2f}</td></tr>\n"
        )

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>GPU Cost Governance Dashboard</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; background: #ffffff; }}
.stat-row {{ display: flex; gap: 20px; margin-bottom: 30px; }}
.stat-card {{ flex: 1; padding: 16px; border-radius: 8px; background: #f5f5f7; text-align: center; }}
.stat-card .value {{ font-size: 28px; font-weight: 700; }}
.stat-card .label {{ font-size: 13px; color: #666; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 30px; }}
th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #eee; }}
th {{ color: #666; font-weight: 600; }}
h1 {{ font-size: 24px; }}
h3 {{ font-size: 15px; color: #444; }}
</style></head>
<body>
<h1>GPU Cost Governance Dashboard</h1>
<p style="color:#888;font-size:13px">Simulated telemetry — see README for what's real (the cost-governance engine) vs. synthetic (the input data).</p>

<div class="stat-row">
  <div class="stat-card"><div class="value">${result['total_cost_usd']:.2f}</div><div class="label">Total spend</div></div>
  <div class="stat-card"><div class="value">${result['total_idle_cost_usd']:.2f}</div><div class="label">Idle (wasted) spend</div></div>
  <div class="stat-card"><div class="value">{result['idle_pct_of_total_spend']}%</div><div class="label">Waste rate</div></div>
  <div class="stat-card"><div class="value">{len(result['alerts'])}</div><div class="label">Active alerts</div></div>
</div>

<h3>By instance</h3>
<table>
<tr><th>Instance</th><th>GPU</th><th>Team</th><th>Total cost</th><th>Idle cost</th><th>Idle %</th><th>Status</th></tr>
{instance_rows}
</table>

<h3>By team</h3>
<table>
<tr><th>Team</th><th>Total cost</th><th>Idle cost</th></tr>
{team_rows}
</table>
</body></html>"""

    DASHBOARD_HTML.write_text(html)
    print(f"Dashboard written to {DASHBOARD_HTML}")
    return DASHBOARD_HTML


if __name__ == "__main__":
    generate_dashboard()
