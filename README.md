# Grafana Cloud Network Device Monitoring Demo

Demonstrates Grafana Cloud's capabilities for monitoring enterprise network infrastructure — routers, switches, and load balancers — using simulated SNMP-style Prometheus metrics.

## What This Demo Shows

A Python-based metrics generator simulates a realistic enterprise network with:

| Device Type | Devices | Key Metrics |
|-------------|---------|-------------|
| **Routers** | `core-rtr-01`, `core-rtr-02` | Interface counters, BGP sessions, OSPF neighbors, routing table size, CPU/memory |
| **Switches** | `access-sw-01`, `access-sw-02`, `dist-sw-01` | Port traffic, MAC table, VLANs, STP changes, PoE power |
| **Load Balancers** | `lb-01`, `lb-02` | Active connections, HTTP request rates, SSL handshakes, pool member health, request latency |

The generator produces dynamic, time-varying data with realistic patterns:
- Business-hours traffic curves
- Occasional BGP flaps and pool member failures (visible in logs)
- Interface error/drop counters that increment slowly
- CPU/memory utilization with periodic spikes

All metrics flow through **Grafana Alloy** to **Grafana Cloud** (Prometheus for metrics, Loki for logs).

## Architecture

```
┌─────────────────────┐        ┌──────────────┐        ┌──────────────────┐
│  network-generator  │◄──scrape──│    Alloy    │──push──►│  Grafana Cloud   │
│  (Prometheus metrics)│        │  (collector)  │        │  Metrics (Mimir)  │
│  :9090/metrics      │        │              │        │  Logs (Loki)      │
└─────────────────────┘        │  Docker logs ─┘        └──────────────────┘
                               └──────────────┘
```

## Prerequisites

| Tool | Required | Install |
|------|----------|---------|
| Make | Yes | Pre-installed on macOS/Linux; WSL: `sudo apt install make` |
| Docker Desktop | Yes | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| GitHub CLI (`gh`) | Yes | [cli.github.com](https://cli.github.com/) |
| BATS | For running tests | [github.com/bats-core/bats-core](https://github.com/bats-core/bats-core) |
| k6 | For load testing | [grafana.com/docs/k6](https://grafana.com/docs/k6/latest/set-up/install-k6/) |

## Quick Start

### 1. Configure Grafana Cloud credentials

```bash
cp .env.example .env
# Edit .env with your Grafana Cloud credentials
# Find them at: grafana.com → My Account → Stack details
```

### 2. Verify prerequisites

```bash
make preflight
```

### 3. Start the demo

```bash
make start
```

This builds the network-generator image, starts all services, and waits for health checks to pass.

### 4. Verify telemetry is flowing

```bash
make test
```

### 5. Browse metrics

Once running, you can browse the raw metrics at `http://localhost:9090/metrics` and query them in Grafana Cloud using PromQL:

```promql
# Device CPU usage across all devices
network_device_cpu_usage_percent

# Interface utilization for routers
network_interface_utilization_percent{role="core"}

# BGP session states
network_bgp_session_state

# Load balancer request rate by status code
rate(network_lb_http_requests_total[5m])

# Pool member health
network_lb_pool_member_status
```

### 6. Add dashboards (optional)

Set up the Grafana MCP server so Claude Code can build dashboards directly:

```bash
claude mcp add --transport stdio grafana \
    --env GRAFANA_URL=https://your-instance.grafana.net \
    --env GRAFANA_API_KEY=glsa_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
    -- docker run -i --rm \
      -e GRAFANA_URL \
      -e GRAFANA_API_KEY \
      mcp/grafana --transport=stdio
```

Then ask Claude Code to create network monitoring dashboards.

### 7. Stop the demo

```bash
make stop
```

## Metric Reference

### Device Metrics (all device types)
| Metric | Type | Description |
|--------|------|-------------|
| `network_device_info` | Info | Device hostname, model, vendor, site, role |
| `network_device_uptime_seconds` | Gauge | Device uptime |
| `network_device_cpu_usage_percent` | Gauge | CPU utilization |
| `network_device_memory_usage_percent` | Gauge | Memory utilization |
| `network_device_temperature_celsius` | Gauge | Temperature by sensor |

### Interface Metrics (all device types)
| Metric | Type | Description |
|--------|------|-------------|
| `network_interface_received_bytes_total` | Counter | Bytes received |
| `network_interface_transmitted_bytes_total` | Counter | Bytes transmitted |
| `network_interface_received_packets_total` | Counter | Packets received |
| `network_interface_transmitted_packets_total` | Counter | Packets transmitted |
| `network_interface_received_errors_total` | Counter | Receive errors |
| `network_interface_transmitted_errors_total` | Counter | Transmit errors |
| `network_interface_received_drops_total` | Counter | Inbound drops |
| `network_interface_transmitted_drops_total` | Counter | Outbound drops |
| `network_interface_speed_bits` | Gauge | Interface speed (bps) |
| `network_interface_oper_status` | Gauge | Operational status (1=up, 0=down) |
| `network_interface_utilization_percent` | Gauge | Bandwidth utilization |

### Router Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `network_bgp_session_state` | Gauge | BGP state (1=established, 0=down) |
| `network_bgp_prefixes_received` | Gauge | Prefixes from peer |
| `network_bgp_session_uptime_seconds` | Gauge | Session uptime |
| `network_bgp_messages_received_total` | Counter | BGP messages in |
| `network_bgp_messages_sent_total` | Counter | BGP messages out |
| `network_ospf_neighbor_count` | Gauge | OSPF neighbors |
| `network_routing_table_entries` | Gauge | Routing table size by protocol |

### Switch Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `network_switch_mac_table_entries` | Gauge | MAC table entries |
| `network_switch_mac_table_capacity` | Gauge | MAC table capacity |
| `network_switch_active_vlans` | Gauge | Active VLAN count |
| `network_switch_stp_topology_changes_total` | Counter | STP changes |
| `network_switch_poe_power_watts` | Gauge | PoE consumption |
| `network_switch_poe_budget_watts` | Gauge | PoE budget |

### Load Balancer Metrics
| Metric | Type | Description |
|--------|------|-------------|
| `network_lb_active_connections` | Gauge | Active connections per VIP |
| `network_lb_connections_total` | Counter | Total connections per VIP |
| `network_lb_received_bytes_total` | Counter | Bytes in per VIP |
| `network_lb_transmitted_bytes_total` | Counter | Bytes out per VIP |
| `network_lb_http_requests_total` | Counter | Requests by status code |
| `network_lb_request_duration_seconds` | Histogram | Request latency |
| `network_lb_ssl_handshakes_total` | Counter | SSL handshakes by TLS version |
| `network_lb_pool_member_status` | Gauge | Member health (1=up, 0=down) |
| `network_lb_pool_member_active_connections` | Gauge | Connections per member |
| `network_lb_connection_table_utilization_percent` | Gauge | Connection table usage |

## Simulated Network Topology

```
            ┌─────────────────────┐
            │   ISP Upstream 1    │
            │   AS65100           │
            └────┬───────────┬────┘
                 │           │
    ┌────────────▼──┐   ┌───▼────────────┐
    │  core-rtr-01  │◄─►│  core-rtr-02   │    ISP Upstream 2 (AS65200)
    │  dc-east      │   │  dc-west       │◄── CDN Peer (AS65300)
    └──┬─────────┬──┘   └──┬──────────┬──┘
       │         │          │          │
  ┌────▼───┐ ┌──▼────┐ ┌───▼───┐ ┌───▼────┐
  │dist-sw │ │  lb-01 │ │ lb-02 │ │        │
  │  -01   │ │dc-east │ │dc-west│ │        │
  └───┬────┘ └───┬────┘ └───┬───┘ │        │
      │          │           │     │        │
  ┌───▼────┐  ┌──▼─────────▼──┐  ┌▼───────┐
  │access  │  │  Web / API /   │  │access  │
  │ sw-01  │  │  App Servers   │  │ sw-02  │
  │dc-east │  │  (pool members)│  │dc-west │
  └────────┘  └────────────────┘  └────────┘
```

## Available Make Targets

| Target | Description |
|--------|-------------|
| `make help` | Show available targets |
| `make preflight` | Run preflight checks |
| `make start` | Start the demo |
| `make stop` | Stop the demo |
| `make test` | Run all tests |
| `make test-smoke` | Run smoke tests only |
| `make test-telemetry` | Run telemetry tests only |
| `make load-test` | Run k6 load test |
| `make clean` | Remove containers, volumes, networks |
