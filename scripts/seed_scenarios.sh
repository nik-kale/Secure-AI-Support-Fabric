#!/bin/bash

# Seed Scenarios Script
# Usage: ./scripts/seed_scenarios.sh [scenario_name]
# Available scenarios: scenario_latency_spike, scenario_config_drift, scenario_auth_error_storm

set -e

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"
SCENARIO_NAME="${1:-scenario_latency_spike}"

echo "================================================"
echo "AI Support Fabric - Seed Scenario Script"
echo "================================================"
echo ""
echo "Gateway URL: $GATEWAY_URL"
echo "Scenario: $SCENARIO_NAME"
echo ""

# Check if gateway is reachable
echo "Checking gateway health..."
if ! curl -s -f "$GATEWAY_URL/health" > /dev/null 2>&1; then
    echo "ERROR: Gateway is not reachable at $GATEWAY_URL"
    echo "Please ensure the lab is running: docker-compose up"
    exit 1
fi

echo "✓ Gateway is healthy"
echo ""

# Function to send telemetry
send_telemetry() {
    local type=$1
    local data=$2

    echo "Sending $type telemetry..."
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$data" \
        "$GATEWAY_URL/api/telemetry/$type" > /dev/null

    if [ $? -eq 0 ]; then
        echo "✓ $type telemetry sent"
    else
        echo "✗ Failed to send $type telemetry"
    fi
}

# Seed based on scenario
case $SCENARIO_NAME in
    scenario_latency_spike)
        echo "Seeding Latency Spike Scenario..."
        echo "This will generate logs showing slow requests and high CPU metrics"
        echo ""

        # Generate slow request logs
        for i in {1..15}; do
            duration=$((5000 + RANDOM % 10000))
            log_data=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "service": "test-service",
    "level": "WARNING",
    "message": "Request took longer than expected",
    "request_id": "req-spike-$i",
    "duration_ms": $duration,
    "expected_duration_ms": 200
}
EOF
)
            send_telemetry "logs" "$log_data"
        done

        # Generate high CPU metrics
        for i in {1..5}; do
            cpu=$((85 + RANDOM % 14))
            latency=$((2000 + RANDOM % 6000))
            metric_data=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "service": "test-service",
    "metrics": {
        "cpu_percent": $cpu,
        "memory_percent": 45,
        "request_rate": 300,
        "error_rate": 8.5,
        "avg_latency_ms": $latency
    }
}
EOF
)
            send_telemetry "metrics" "$metric_data"
        done

        echo ""
        echo "✓ Latency spike scenario seeded successfully!"
        ;;

    scenario_config_drift)
        echo "Seeding Config Drift Scenario..."
        echo "This will generate a configuration change event with security drift"
        echo ""

        config_data=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "service": "test-service",
    "config_version": "1.0.1-drift",
    "configuration": {
        "debug_mode": true,
        "log_level": "DEBUG",
        "max_connections": 100,
        "timeout_seconds": 30,
        "rate_limit": 1000,
        "enable_auth": true,
        "tls_enabled": true
    },
    "changed_by": "unknown",
    "change_reason": "Unauthorized change detected"
}
EOF
)
        send_telemetry "config" "$config_data"

        echo ""
        echo "✓ Config drift scenario seeded successfully!"
        ;;

    scenario_auth_error_storm)
        echo "Seeding Auth Error Storm Scenario..."
        echo "This will generate multiple authentication failure logs"
        echo ""

        # Generate auth failure logs
        for i in {1..30}; do
            user=$((1 + RANDOM % 5))
            ip=$((1 + RANDOM % 3))
            log_data=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "service": "test-service",
    "level": "ERROR",
    "message": "Authentication failed",
    "request_id": "req-auth-$i",
    "user": "user_$user",
    "reason": "Invalid credentials",
    "source_ip": "192.168.1.$ip"
}
EOF
)
            send_telemetry "logs" "$log_data"
        done

        # Generate some high CPU metrics
        for i in {1..3}; do
            cpu=$((70 + RANDOM % 15))
            metric_data=$(cat <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "service": "test-service",
    "metrics": {
        "cpu_percent": $cpu,
        "memory_percent": 48,
        "request_rate": 250,
        "error_rate": 15.5,
        "avg_latency_ms": 180
    }
}
EOF
)
            send_telemetry "metrics" "$metric_data"
        done

        echo ""
        echo "✓ Auth error storm scenario seeded successfully!"
        ;;

    *)
        echo "ERROR: Unknown scenario '$SCENARIO_NAME'"
        echo ""
        echo "Available scenarios:"
        echo "  - scenario_latency_spike"
        echo "  - scenario_config_drift"
        echo "  - scenario_auth_error_storm"
        echo ""
        echo "Usage: $0 [scenario_name]"
        exit 1
        ;;
esac

echo ""
echo "================================================"
echo "Next Steps:"
echo "================================================"
echo ""
echo "1. Trigger AI analysis:"
echo "   curl -X POST $GATEWAY_URL/api/run-analysis"
echo ""
echo "2. View findings:"
echo "   curl $GATEWAY_URL/api/ai/findings"
echo ""
echo "3. View remediation plans:"
echo "   curl $GATEWAY_URL/api/ai/remediation"
echo ""
echo "4. Open dashboard:"
echo "   http://localhost:3000"
echo ""
