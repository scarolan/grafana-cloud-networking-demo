# Demo Builder

A template for Grafana SEs to rapidly build customer demos that ship telemetry (metrics, logs, traces) to Grafana Cloud.

**How it works:** Copy this template, describe your demo scenario to Claude Code, and it builds out the infrastructure, telemetry pipeline, and tests for you.

## Prerequisites

| Tool | Required | Install |
|------|----------|---------|
| Make | Yes | Pre-installed on macOS/Linux; WSL: `sudo apt install make` |
| Docker Desktop | Yes | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| GitHub CLI (`gh`) | Yes | [cli.github.com](https://cli.github.com/) |
| Claude Code | Yes | [docs.anthropic.com/claude-code](https://docs.anthropic.com/en/docs/claude-code) |
| Terraform | If demo needs cloud resources | [terraform.io/downloads](https://www.terraform.io/downloads) |
| k6 | For load testing | [grafana.com/docs/k6](https://grafana.com/docs/k6/latest/set-up/install-k6/) |
| BATS | For running tests | [github.com/bats-core/bats-core](https://github.com/bats-core/bats-core) |

## Quick Start

### 1. Create your demo repo from this template

Name it `grafana-cloud-<technology>-demo` (e.g., `grafana-cloud-oracle-demo`, `grafana-cloud-mssql-demo`):

```bash
gh repo create grafana-cloud-mytech-demo --template grafana/demo-builder --private
sleep 5
gh repo clone grafana-cloud-mytech-demo
cd grafana-cloud-mytech-demo
```

### 2. Configure Grafana Cloud credentials

```bash
cp .env.example .env
# Edit .env with your Grafana Cloud credentials
# Find them at: grafana.com → My Account → Stack details
```

### 3. Verify prerequisites

```bash
make preflight
```

### 4. Add Grafana MCP server (for dashboards)

Create a Service Account with **Editor** role in your Grafana Cloud instance (Administration > Service Accounts), generate a token, then:

```bash
claude mcp add --transport stdio grafana \
    --env GRAFANA_URL=https://your-instance.grafana.net \
    --env GRAFANA_API_KEY=glsa_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
    -- docker run -i --rm \
      -e GRAFANA_URL \
      -e GRAFANA_API_KEY \
      mcp/grafana --transport=stdio
```

This lets Claude Code create and edit dashboards directly in your Grafana Cloud instance.

### 5. Describe your scenario to Claude Code

```bash
claude
```

Tell Claude what you're demoing. For example:
> "I need a demo showing a Python Flask app with PostgreSQL. The app should expose REST endpoints, emit traces via OpenTelemetry, and I need to show database query metrics in Grafana Cloud."

Claude Code reads `CLAUDE.md` and follows the 10-step workflow to build your demo.

### 6. Start, test, and demo

```bash
make start          # Start all services
make test           # Verify everything works
make load-test      # Generate traffic (optional)
make stop           # Tear down when done
```

## Template Structure

```
├── CLAUDE.md                    # Guide for Claude Code (the brain)
├── README.md                    # This file
├── Makefile                     # Task runner (run 'make help')
├── .env.example                 # Grafana Cloud credentials template
├── .gitignore                   # Prevents secrets from being committed
├── docker-compose.yml           # Services (Alloy + your demo apps)
├── alloy/
│   └── config.alloy             # Telemetry pipeline configuration
├── terraform/                   # Cloud infrastructure (when needed)
│   ├── providers.tf
│   ├── variables.tf
│   ├── main.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
├── scripts/
│   ├── preflight-check.sh       # Prerequisite verification
│   ├── start-demo.sh            # Start everything
│   └── stop-demo.sh             # Stop everything
├── tests/
│   ├── README.md                # Testing guide
│   ├── preflight.bats           # Tool/config checks
│   ├── smoke.bats               # Service health checks
│   └── telemetry.bats           # Data flow verification
├── k6/
│   ├── README.md                # Load testing guide
│   └── load-test.js             # k6 load test script
└── dashboards/
    └── README.md                # Dashboard export/import instructions
```

## Conventions

- **Docker Compose V2** — `docker compose` (space, not hyphen)
- **Pinned image versions** — no `:latest` tags
- **Health checks on every service** — enables reliable `depends_on`
- **All secrets in `.env`** — never hardcoded
- **Local Terraform state** — demos are ephemeral, no remote backends
- **BATS for testing** — purpose-built for CLI/infrastructure verification
- **Dashboards via Grafana MCP** — Claude Code pushes dashboards directly to Grafana Cloud

## Available Make Targets

Run `make help` to see all targets:

| Target | Description |
|--------|-------------|
| `make help` | Show available targets |
| `make preflight` | Run preflight checks |
| `make start` | Start the demo |
| `make stop` | Stop the demo |
| `make test` | Run all tests |
| `make test-preflight` | Run preflight tests only |
| `make test-smoke` | Run smoke tests only |
| `make test-telemetry` | Run telemetry tests only |
| `make load-test` | Run k6 load test |
| `make clean` | Remove containers, volumes, networks |

## Graduating a Demo

When a demo is polished enough to share across the SE team:

1. Ensure all tests pass (`make test`)
2. Update this README with demo-specific documentation
3. Export and commit dashboards to `dashboards/`
4. Request transfer to the grafana org via your team lead
