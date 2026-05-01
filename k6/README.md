# k6 Load Tests

Load tests generate realistic traffic for your demo, producing telemetry data that shows up in Grafana dashboards.

## Prerequisites

k6 runs inside the Docker network via `make load-test` — no local install needed.

For local installs (optional): https://grafana.com/docs/k6/latest/set-up/install-k6/

## Running

```bash
# Run inside Docker network (preferred — can reach all internal services)
make load-test

# Or directly via docker compose
docker compose --profile load-test run --rm k6 run /scripts/load-test.js

# Custom base URL (use Docker service names for internal services)
docker compose --profile load-test run --rm -e BASE_URL=http://my-app:3000 k6 run /scripts/load-test.js
```

## Running in Grafana Cloud k6

```bash
K6_CLOUD_TOKEN=<your-token> k6 cloud k6/load-test.js
```

Get your token from: grafana.com > My Account > k6 Cloud > API Token

## Customizing

Edit `k6/load-test.js` to:

1. **Target your demo's endpoints** — Replace the example health check with real API calls
2. **Adjust the load profile** — Modify `stages` for different ramp-up/hold/ramp-down patterns
3. **Set thresholds** — Define what "acceptable performance" means for your demo
4. **Add checks** — Validate response bodies, headers, and status codes
