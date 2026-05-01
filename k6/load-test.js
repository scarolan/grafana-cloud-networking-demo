import http from 'k6/http';
import { check, sleep } from 'k6';

// =============================================================================
// k6 Load Test — Demo Builder Template
// =============================================================================
// Edit this file to target your demo's endpoints and generate realistic traffic.
//
// Run locally:   k6 run k6/load-test.js
// Run in cloud:  K6_CLOUD_TOKEN=<token> k6 cloud k6/load-test.js
// =============================================================================

export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Ramp up to 10 virtual users
    { duration: '1m', target: 10 },   // Hold steady at 10 VUs
    { duration: '30s', target: 0 },   // Ramp down to 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests complete under 500ms
    http_req_failed: ['rate<0.01'],    // Less than 1% failure rate
  },
};

// Base URL for your demo application
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export default function () {
  // --- Replace with your demo's endpoints ---

  // Example: Health check
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    'health check returns 200': (r) => r.status === 200,
  });

  // Example: API endpoint
  // const apiRes = http.get(`${BASE_URL}/api/v1/data`);
  // check(apiRes, {
  //   'api returns 200': (r) => r.status === 200,
  //   'api response has data': (r) => r.json().data !== undefined,
  // });

  // Example: POST request
  // const payload = JSON.stringify({ key: 'value' });
  // const params = { headers: { 'Content-Type': 'application/json' } };
  // const postRes = http.post(`${BASE_URL}/api/v1/items`, payload, params);
  // check(postRes, {
  //   'create returns 201': (r) => r.status === 201,
  // });

  // Simulate user think time
  sleep(1);
}
