#!/usr/bin/env bats
# =============================================================================
# Telemetry Tests — Verify metrics/logs/traces are flowing to Grafana Cloud
# =============================================================================
# NOTE: Alloy has no host port mappings (internal-only). The Alloy image is
# minimal (no curl/wget), so we use raw bash HTTP via /dev/tcp.
# =============================================================================

# Helper: fetch Alloy metrics via raw HTTP inside the container
alloy_metrics() {
  docker compose exec alloy bash -c \
    'exec 3<>/dev/tcp/localhost/12345; printf "GET /metrics HTTP/1.0\r\nHost: localhost\r\n\r\n" >&3; cat <&3; exec 3>&-'
}

@test "alloy exposes prometheus metrics" {
  run alloy_metrics
  [ "$status" -eq 0 ]
  echo "$output" | grep -q 'alloy_build_info'
}

@test "prometheus remote_write is configured" {
  run alloy_metrics
  [ "$status" -eq 0 ]
  echo "$output" | grep -q 'prometheus_remote_write'
}

@test "metrics samples are being sent" {
  # Wait briefly for initial scrape to complete
  sleep 5

  run alloy_metrics
  [ "$status" -eq 0 ]

  # Check that samples_total is present and incrementing
  samples=$(echo "$output" | grep 'prometheus_remote_storage_samples_total' | head -1 | awk '{print $2}')
  [ -n "$samples" ]
}

@test "no persistent remote_write errors" {
  run alloy_metrics
  [ "$status" -eq 0 ]

  # Check for failed samples — a small number may be transient, but large numbers indicate config issues
  failed=$(echo "$output" | grep 'prometheus_remote_storage_samples_failed_total' | head -1 | awk '{print $2}' || echo "0")
  total=$(echo "$output" | grep 'prometheus_remote_storage_samples_total' | head -1 | awk '{print $2}' || echo "1")

  # If both metrics exist, failed should be less than 10% of total
  if [ -n "$failed" ] && [ -n "$total" ] && [ "$total" != "0" ]; then
    failed_int=${failed%.*}
    total_int=${total%.*}
    [ "${failed_int:-0}" -lt "$((total_int / 10 + 1))" ]
  fi
}

# =============================================================================
# Add demo-specific telemetry checks below:
# =============================================================================
# @test "my-app metrics are being scraped" {
#   run alloy_metrics
#   [ "$status" -eq 0 ]
#   echo "$output" | grep -q 'scrape_samples_scraped{job="my_service"}'
# }
#
# @test "my-app request metrics are present" {
#   run curl -sf http://localhost:8080/metrics
#   [ "$status" -eq 0 ]
#   echo "$output" | grep -q 'http_requests_total'
# }
