import requests
from mcp.server.fastmcp import FastMCP

# Create MCP server
mcp = FastMCP(
    name="PrometheusMetricsReader"
)

PROM_URL = "http://localhost:9090/metrics"


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


if __name__ == "__main__":
    mcp.run(transport="stdio")
