#!/usr/bin/env bats
# =============================================================================
# Smoke Tests — Verify demo services are running and healthy
# =============================================================================
# NOTE: Alloy has no host port mappings (internal-only). Tests reach it via
# "docker compose exec". The Alloy image is minimal (no curl/wget), so we
# use bash /dev/tcp probes for connectivity and raw HTTP for content.
# =============================================================================

@test "alloy container is running" {
  run docker compose ps --format json alloy
  [ "$status" -eq 0 ]
  echo "$output" | grep -q '"State":"running"'
}

@test "alloy container is healthy" {
  container_id=$(docker compose ps -q alloy)
  run docker inspect --format='{{.State.Health.Status}}' "$container_id"
  [ "$status" -eq 0 ]
  [ "$output" = "healthy" ]
}

@test "alloy ready endpoint is accessible" {
  run docker compose exec alloy bash -c 'echo > /dev/tcp/localhost/12345'
  [ "$status" -eq 0 ]
}

@test "alloy metrics endpoint is accessible" {
  run docker compose exec alloy bash -c \
    'exec 3<>/dev/tcp/localhost/12345; printf "GET /metrics HTTP/1.0\r\nHost: localhost\r\n\r\n" >&3; cat <&3; exec 3>&-'
  [ "$status" -eq 0 ]
  echo "$output" | grep -q 'alloy_build_info'
}

# =============================================================================
# Network generator service checks
# =============================================================================

@test "network-generator container is running" {
  run docker compose ps --format json network-generator
  [ "$status" -eq 0 ]
  echo "$output" | grep -q '"State":"running"'
}

@test "network-generator container is healthy" {
  container_id=$(docker compose ps -q network-generator)
  run docker inspect --format='{{.State.Health.Status}}' "$container_id"
  [ "$status" -eq 0 ]
  [ "$output" = "healthy" ]
}

@test "network-generator metrics endpoint is accessible" {
  run curl -sf http://localhost:9090/metrics
  [ "$status" -eq 0 ]
}

@test "network-generator exposes device info metrics" {
  run curl -sf http://localhost:9090/metrics
  [ "$status" -eq 0 ]
  echo "$output" | grep -q 'network_device_info'
}

@test "network-generator exposes router metrics" {
  run curl -sf http://localhost:9090/metrics
  [ "$status" -eq 0 ]
  echo "$output" | grep -q 'network_bgp_session_state'
  echo "$output" | grep -q 'network_routing_table_entries'
}

@test "network-generator exposes switch metrics" {
  run curl -sf http://localhost:9090/metrics
  [ "$status" -eq 0 ]
  echo "$output" | grep -q 'network_switch_mac_table_entries'
  echo "$output" | grep -q 'network_switch_poe_power_watts'
}

@test "network-generator exposes load balancer metrics" {
  run curl -sf http://localhost:9090/metrics
  [ "$status" -eq 0 ]
  echo "$output" | grep -q 'network_lb_active_connections'
  echo "$output" | grep -q 'network_lb_pool_member_status'
}
