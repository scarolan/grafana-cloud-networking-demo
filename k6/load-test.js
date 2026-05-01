import http from 'k6/http';
import { check, sleep } from 'k6';

// =============================================================================
// k6 Load Test — Network Monitoring Demo
// =============================================================================
// Hits the Prometheus metrics endpoint on the network generator to simulate
// a monitoring system polling the exporter at scale.
//
// Run locally:   k6 run k6/load-test.js
// Run in Docker: docker compose --profile load-test run --rm k6 run /scripts/load-test.js
// =============================================================================

export const options = {
  stages: [
    { duration: '30s', target: 5 },   // Ramp up — simulate multiple scrapers
    { duration: '2m', target: 5 },    // Hold steady — sustained polling
    { duration: '30s', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // Metrics endpoint should respond under 2s
    http_req_failed: ['rate<0.01'],
  },
};

const GENERATOR_URL = __ENV.GENERATOR_URL || 'http://network-generator:9090';

export default function () {
  const metricsRes = http.get(`${GENERATOR_URL}/metrics`);
  check(metricsRes, {
    'metrics endpoint returns 200': (r) => r.status === 200,
    'response contains device metrics': (r) => r.body.includes('network_device_cpu_usage_percent'),
    'response contains interface metrics': (r) => r.body.includes('network_interface_received_bytes_total'),
    'response contains bgp metrics': (r) => r.body.includes('network_bgp_session_state'),
    'response contains lb metrics': (r) => r.body.includes('network_lb_active_connections'),
  });

  sleep(3);
}
