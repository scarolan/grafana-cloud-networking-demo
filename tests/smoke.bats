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
# Add demo-specific service checks below:
# =============================================================================
# @test "my-app container is running" {
#   run docker compose ps --format json my-app
#   [ "$status" -eq 0 ]
#   echo "$output" | grep -q '"State":"running"'
# }
#
# @test "my-app container is healthy" {
#   container_id=$(docker compose ps -q my-app)
#   run docker inspect --format='{{.State.Health.Status}}' "$container_id"
#   [ "$status" -eq 0 ]
#   [ "$output" = "healthy" ]
# }
#
# @test "my-app is accessible on port 8080" {
#   run curl -sf http://localhost:8080/health
#   [ "$status" -eq 0 ]
# }
