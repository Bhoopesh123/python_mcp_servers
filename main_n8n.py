import requests
from mcp.server.fastmcp import FastMCP

# Create MCP server
mcp = FastMCP(
    name="PrometheusMetricsReader"
)

PROM_URL = "http://prometheus:9090/metrics"

# Grafana settings
GRAFANA_URL = "http://grafana:3000"
GRAFANA_API_KEY = "glsa_zEm32fiuZZREY21hUA9NW8iBgtUmPF8b_2cb1caef"

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

@mcp.tool()
def update_grafana_dashboard(dashboard_uid: str, new_title: str, promql: str) -> str:
    """
    Update an existing Grafana dashboard:
    - Change dashboard title
    - Add a new panel OR update existing panel
    """

    # 1️⃣ Get dashboard JSON from Grafana
    get_url = f"{GRAFANA_URL}/api/dashboards/uid/{dashboard_uid}"
    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(get_url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"Error fetching dashboard: {str(e)}"

    dashboard = data.get("dashboard")
    if not dashboard:
        return "Dashboard JSON malformed or empty."

    # 2️⃣ Update dashboard title
    dashboard["title"] = new_title

    # 3️⃣ Add or update a panel
    existing_panels = dashboard.get("panels", [])

    new_panel = {
        "id": len(existing_panels) + 1,
        "title": f"Updated Panel - {new_title}",
        "type": "timeseries",
        "gridPos": {"x": 0, "y": 8 * len(existing_panels), "w": 24, "h": 8},
        "targets": [
            {
                "expr": promql,
                "legendFormat": "{{instance}}"
            }
        ]
    }

    # Append new panel
    existing_panels.append(new_panel)
    dashboard["panels"] = existing_panels

    # 4️⃣ POST updated dashboard back to Grafana
    update_url = f"{GRAFANA_URL}/api/dashboards/db"
    payload = {
        "dashboard": dashboard,
        "overwrite": True
    }

    try:
        update_resp = requests.post(update_url, json=payload, headers=headers)
        update_resp.raise_for_status()
        return f"Dashboard '{new_title}' updated successfully with new panel!"
    except Exception as e:
        return f"Error updating dashboard: {str(e)}"


@mcp.tool()
def get_dashboard_uid(dashboard_name: str) -> str:
    """
    Search Grafana dashboards by name and return the UID.
    """
    url = f"{GRAFANA_URL}/api/search?query={dashboard_name}&type=dash-db"
    headers = {
        "Authorization": f"Bearer {GRAFANA_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return f"No dashboard found with name '{dashboard_name}'"
        # Return the first matching UID
        uid = data[0].get("uid")
        title = data[0].get("title")
        return f"Dashboard found: {title}, UID: {uid}"
    except Exception as e:
        return f"Error fetching dashboard UID: {str(e)}"

@mcp.tool()
def trigger_n8n_get(webhook_url: str) -> str:
    """
    Trigger an n8n workflow using GET webhook.
    
    Example:
        trigger_n8n_get("http://localhost:5678/webhook/21f849fe-cb04-4b69-ac47-22fd0cbb9037")
    """

    try:
        resp = requests.get(webhook_url, timeout=5)
        return f"n8n GET Response ({resp.status_code}): {resp.text}"
    except Exception as e:
        return f"Error calling n8n GET webhook: {str(e)}"


# ======================================================================
if __name__ == "__main__":
    mcp.run(transport="stdio")
