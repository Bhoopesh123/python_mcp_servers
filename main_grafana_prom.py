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
# 1. Get all metrics
# ======================================================================
@mcp.tool()
def get_all_metrics() -> str:
    """
    Fetch raw Prometheus /metrics text from local Prometheus server.
    """
    try:
        resp = requests.get(PROM_URL, timeout=5)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return f"Error fetching metrics: {str(e)}"

# ======================================================================
# 2. Search for a specific metric
# ======================================================================
@mcp.tool()
def search_metric(metric_name: str) -> str:
    """
    Search inside Prometheus /metrics output for a specific metric name.
    """
    try:
        resp = requests.get(PROM_URL, timeout=5)
        resp.raise_for_status()
        lines = resp.text.splitlines()
        matched = [l for l in lines if metric_name in l]
        return "\n".join(matched) if matched else "No such metric found"
    except Exception as e:
        return f"Error searching metrics: {str(e)}"

# ======================================================================
# 3. Create Grafana Dashboard
# ======================================================================
@mcp.tool()
def create_grafana_dashboard(dashboard_name: str) -> str:
    """
    Create a Grafana dashboard automatically using Grafana HTTP API.
    """

    url = f"{GRAFANA_URL}/api/dashboards/db"
    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "dashboard": {
            "id": None,
            "title": dashboard_name,
            "panels": [
                {
                    "title": "Node CPU Usage",
                    "type": "graph",
                    "gridPos": {"x": 0, "y": 0, "w": 24, "h": 8},
                    "targets": [
                        {
                            "expr": '100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
                            "legendFormat": "{{instance}} CPU"
                        }
                    ]
                }
            ],
            "schemaVersion": 36,
            "version": 1
        },
        "overwrite": True
    }

    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return f"Dashboard '{dashboard_name}' created successfully!"
    except Exception as e:
        return f"Error creating dashboard: {str(e)}"

# ======================================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")
