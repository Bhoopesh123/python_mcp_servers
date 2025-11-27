import requests
from mcp.server.fastmcp import FastMCP

# Create MCP server
mcp = FastMCP(
    name="PrometheusMetricsReader"
)

PROM_URL = "http://localhost:9090/metrics"

# Grafana settings
GRAFANA_URL = "http://localhost:3000"
GRAFANA_API_KEY = "glsa_AQn2yCE7i6khnhA9l9RFQG9xK3pEyEzy_568ba0aa"

# ======================================================================
# 1. Search Prometheus metrics
# ======================================================================
def _get_metrics_text():
    resp = requests.get(PROM_URL, timeout=5)
    resp.raise_for_status()
    return resp.text


@mcp.tool()
def search_metric(metric_name: str) -> str:
    """
    Search inside Prometheus /metrics output for a specific metric name.
    """
    try:
        text = _get_metrics_text()
        lines = text.splitlines()
        matched = [l for l in lines if metric_name in l]
        return "\n".join(matched) if matched else "No such metric found"
    except Exception as e:
        return f"Error searching metrics: {str(e)}"


# ======================================================================
# 2. Auto-generate PromQL from metric
# ======================================================================
def generate_promql(metric_name: str) -> str:
    """
    Create PromQL automatically depending on metric type
    """
    # COUNTER metrics => use rate()
    if metric_name.endswith("_total") or metric_name.endswith("_count"):
        return f"rate({metric_name}[5m])"

    # GAUGE metrics => use direct metric
    return metric_name


# ======================================================================
# 3. Create a Grafana dashboard with auto-promql
# ======================================================================
def _grafana_headers():
    return {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json"
    }


def create_dashboard(dashboard_name: str, promql: str) -> str:
    url = f"{GRAFANA_URL}/api/dashboards/db"

    payload = {
        "dashboard": {
            "id": None,
            "title": dashboard_name,
            "panels": [
                {
                    "title": f"Auto: {dashboard_name}",
                    "type": "timeseries",
                    "gridPos": {"x": 0, "y": 0, "w": 24, "h": 8},
                    "targets": [
                        {
                            "expr": promql,
                            "legendFormat": "{{instance}}"
                        }
                    ]
                }
            ],
            "schemaVersion": 36,
            "version": 1
        },
        "overwrite": True
    }

    resp = requests.post(url, json=payload, headers=_grafana_headers())
    if resp.status_code != 200:
        return f"Grafana Error {resp.status_code}: {resp.text}"

    return f"Dashboard '{dashboard_name}' created with PromQL: {promql}"


# ======================================================================
# 4. AUTO mode: Search metric → Generate PromQL → Create dashboard
# ======================================================================
@mcp.tool()
def auto_dashboard(metric_name: str) -> str:
    """
    Fully automated:
    1. Search Prometheus metrics
    2. Generate PromQL
    3. Create Grafana dashboard
    """

    # Step 1: Check if metric exists
    search_result = search_metric(metric_name)
    if search_result.startswith("No such metric"):
        return f"Metric '{metric_name}' not found in Prometheus."

    # Step 2: Auto-create PromQL
    promql = generate_promql(metric_name)

    # Step 3: Create Grafana dashboard
    dashboard_name = f"Auto Dashboard: {metric_name}"
    result = create_dashboard(dashboard_name, promql)

    return (
        f"✅ Metric found: {metric_name}\n"
        f"📌 PromQL used: {promql}\n"
        f"📊 Result: {result}"
    )


# ======================================================================
if __name__ == "__main__":
    mcp.run(transport="stdio")
