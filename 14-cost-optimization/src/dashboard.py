"""Generates a self-contained HTML dashboard from the cost ledger — no
external charting library, plain HTML/CSS bars sized by inline style, so
the output is a single file you can open directly in a browser with zero
setup.
"""

from cost_ledger import get_connection, summary
from config import DASHBOARD_HTML


def fetch_requests(conn):
    rows = conn.execute(
        "SELECT timestamp, query, cache_hit, similarity, tokens, actual_cost_usd, would_be_cost_usd "
        "FROM requests ORDER BY id"
    ).fetchall()
    return rows


def generate_dashboard():
    conn = get_connection()
    stats = summary(conn)
    rows = fetch_requests(conn)

    table_rows = ""
    for ts, query, hit, sim, tokens, actual, would_be in rows:
        badge = '<span style="color:#0a7d32;font-weight:600">HIT</span>' if hit else '<span style="color:#888">MISS</span>'
        sim_str = f"{sim:.3f}" if sim is not None else "—"
        table_rows += (
            f"<tr><td>{badge}</td><td>{query}</td><td>{sim_str}</td>"
            f"<td>{tokens}</td><td>${actual:.6f}</td><td>${would_be:.6f}</td></tr>\n"
        )

    hit_rate_pct = stats["cache_hit_rate"] * 100
    savings_pct = stats["savings_pct"]

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Cost Optimization Dashboard</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; color: #1a1a1a; background: #ffffff; padding: 0 20px; }}
.stat-row {{ display: flex; gap: 20px; margin-bottom: 30px; }}
.stat-card {{ flex: 1; padding: 16px; border-radius: 8px; background: #f5f5f7; text-align: center; }}
.stat-card .value {{ font-size: 28px; font-weight: 700; }}
.stat-card .label {{ font-size: 13px; color: #666; margin-top: 4px; }}
.bar-bg {{ background: #e5e5e5; border-radius: 4px; height: 20px; overflow: hidden; margin: 8px 0 24px; }}
.bar-fill {{ background: #0a7d32; height: 100%; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #eee; }}
th {{ color: #666; font-weight: 600; }}
</style></head>
<body>
<h1>Aegis RAG — Cost Optimization Dashboard</h1>

<div class="stat-row">
  <div class="stat-card"><div class="value">{stats['total_requests']}</div><div class="label">Total requests</div></div>
  <div class="stat-card"><div class="value">{stats['cache_hits']}</div><div class="label">Cache hits</div></div>
  <div class="stat-card"><div class="value">{hit_rate_pct:.1f}%</div><div class="label">Cache hit rate</div></div>
  <div class="stat-card"><div class="value">${stats['savings_usd']:.6f}</div><div class="label">Savings this run</div></div>
</div>

<h3>Cost savings from semantic caching: {savings_pct:.1f}%</h3>
<div class="bar-bg"><div class="bar-fill" style="width:{min(savings_pct,100):.1f}%"></div></div>

<h3>Request log</h3>
<table>
<tr><th>Result</th><th>Query</th><th>Similarity</th><th>Tokens</th><th>Actual cost</th><th>Would-be cost</th></tr>
{table_rows}
</table>
</body></html>"""

    DASHBOARD_HTML.write_text(html)
    print(f"Dashboard written to {DASHBOARD_HTML}")
    return DASHBOARD_HTML


if __name__ == "__main__":
    generate_dashboard()
