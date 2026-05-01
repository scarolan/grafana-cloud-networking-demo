# Dashboards

This directory contains exported Grafana dashboard JSON files. Other SEs can import these directly into their Grafana Cloud instances.

## Building Dashboards with Claude Code + Grafana MCP

The fastest way to build dashboards is to give Claude Code direct access to your Grafana instance via the [Grafana MCP server](https://github.com/grafana/mcp-grafana):

```bash
claude mcp add --transport stdio grafana \
    --env GRAFANA_URL=https://your-instance.grafana.net \
    --env GRAFANA_API_KEY=glsa_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
    -- docker run -i --rm \
      -e GRAFANA_URL \
      -e GRAFANA_API_KEY \
      mcp/grafana --transport=stdio
```

Once configured, Claude Code can create, edit, and push dashboards directly. No manual export/import needed. Just describe what you want:

> "Build me a dashboard showing MSSQL connection health, query latency, and error rates"

After Claude builds the dashboard, export the JSON and commit it to this directory so other SEs can import it.

## Reference Dashboard

`example-mssql-overview.json` is a reference dashboard from the MSSQL demo. It demonstrates good patterns:
- Stat panels for at-a-glance health (server status, uptime, connections)
- Time series panels for trends (batch requests/sec, query latency)
- Log panels integrated alongside metrics
- Consistent use of Prometheus data source queries

Use this as a starting point when building dashboards for new demos.

## Exporting Dashboards

1. Open the dashboard in Grafana
2. Click **Share** (top-right)
3. Select **Export**
4. Click **Save to file**
5. Save the JSON file to this directory with a descriptive name:
   ```
   dashboards/demo-overview.json
   dashboards/service-health.json
   dashboards/telemetry-pipeline.json
   ```

## Importing Dashboards

To import a dashboard from this repo into your Grafana Cloud instance:

1. Open Grafana Cloud
2. Go to **Dashboards** > **New** > **Import**
3. Click **Upload dashboard JSON file**
4. Select the `.json` file from this directory
5. Choose your Prometheus and Loki data sources when prompted
6. Click **Import**

## Dashboard Inventory

<!-- Update this table as you add dashboards -->
| File | Description |
|------|-------------|
| `example-mssql-overview.json` | Reference dashboard from MSSQL demo — server health, queries, latency, logs |
