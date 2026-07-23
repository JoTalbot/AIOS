#!/bin/bash
# AIOS Health Check Script
# Usage: ./scripts/health_check.sh [--verbose] [--json]

set -e

VERBOSE=false
JSON_OUTPUT=false
API_URL="${AIOS_API_URL:-http://localhost:8000}"
DASHBOARD_URL="${AIOS_DASHBOARD_URL:-http://localhost:8080}"
GRAFANA_URL="${AIOS_GRAFANA_URL:-http://localhost:3000}"

# Parse arguments
for arg in "$@"; do
    case $arg in
        --verbose|-v)
            VERBOSE=true
            ;;
        --json|-j)
            JSON_OUTPUT=true
            ;;
        --help|-h)
            echo "Usage: $0 [--verbose] [--json]"
            echo ""
            echo "Options:"
            echo "  --verbose, -v    Show detailed output"
            echo "  --json, -j       Output in JSON format"
            echo "  --help, -h       Show this help"
            exit 0
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Results array for JSON
declare -a RESULTS=()

# Function to check and report
check() {
    local name="$1"
    local status="$2"  # pass, fail, warn
    local message="$3"
    local details="${4:-}"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    case $status in
        pass)
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            if [ "$JSON_OUTPUT" = false ]; then
                echo -e "${GREEN}✅${NC} $name: $message"
            fi
            ;;
        fail)
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            if [ "$JSON_OUTPUT" = false ]; then
                echo -e "${RED}❌${NC} $name: $message"
            fi
            ;;
        warn)
            WARNINGS=$((WARNINGS + 1))
            if [ "$JSON_OUTPUT" = false ]; then
                echo -e "${YELLOW}⚠️${NC}  $name: $message"
            fi
            ;;
    esac
    
    if [ "$VERBOSE" = true ] && [ -n "$details" ] && [ "$JSON_OUTPUT" = false ]; then
        echo -e "   ${BLUE}└─${NC} $details"
    fi
    
    # Add to results array for JSON
    RESULTS+=("{\"name\":\"$name\",\"status\":\"$status\",\"message\":\"$message\",\"details\":\"$details\"}")
}

# Function to check HTTP endpoint
check_http() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"
    
    local http_status
    http_status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
    
    if [ "$http_status" = "$expected_status" ]; then
        check "$name" "pass" "HTTP $http_status" "$url"
    elif [ "$http_status" = "000" ]; then
        check "$name" "fail" "Connection failed" "$url"
    else
        check "$name" "fail" "HTTP $http_status (expected $expected_status)" "$url"
    fi
}

# Function to check service
check_service() {
    local name="$1"
    local container="$2"
    
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        local status
        status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
        
        if [ "$status" = "running" ]; then
            check "$name" "pass" "Running" "Container: $container"
        else
            check "$name" "fail" "Status: $status" "Container: $container"
        fi
    else
        check "$name" "fail" "Not found" "Container: $container"
    fi
}

# Function to check test count
check_tests() {
    local test_count
    test_count=$(python3 -m pytest --collect-only -q 2>/dev/null | tail -1 | grep -oP '\d+' || echo "0")
    
    if [ "$test_count" -ge 1000 ]; then
        check "Test suite" "pass" "$test_count tests" "Minimum: 1000"
    elif [ "$test_count" -ge 500 ]; then
        check "Test suite" "warn" "$test_count tests" "Below recommended: 1000"
    else
        check "Test suite" "fail" "$test_count tests" "Critical: below 500"
    fi
}

# Function to check API endpoints
check_api_endpoints() {
    local endpoints=(
        "API Health:/health"
        "API Metrics:/metrics"
        "API Stats:/api/v1/stats"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local name="${endpoint%%:*}"
        local path="${endpoint##*:}"
        check_http "$name" "${API_URL}${path}"
    done
}

# Function to check webhooks
check_webhooks() {
    local webhook_health
    webhook_health=$(python3 aios_cli.py admin webhooks health 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        local total
        total=$(echo "$webhook_health" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_targets', 0))" 2>/dev/null || echo "0")
        
        if [ "$total" -gt 0 ]; then
            check "Webhooks" "pass" "$total targets configured"
        else
            check "Webhooks" "warn" "No targets configured"
        fi
    else
        check "Webhooks" "warn" "Unable to check" "CLI not available"
    fi
}

# Function to check backups
check_backups() {
    local backup_health
    backup_health=$(python3 aios_cli.py admin backup health 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        local total
        total=$(echo "$backup_health" | python3 -c "import sys, json; print(json.load(sys.stdin).get('health', {}).get('total_backups', 0))" 2>/dev/null || echo "0")
        
        if [ "$total" -gt 0 ]; then
            check "Backups" "pass" "$total backups available"
        else
            check "Backups" "warn" "No backups found"
        fi
    else
        check "Backups" "warn" "Unable to check" "CLI not available"
    fi
}

# Function to check database
check_database() {
    if [ -f "aios.sqlite" ]; then
        local size
        size=$(du -h aios.sqlite | cut -f1)
        check "Database" "pass" "aios.sqlite ($size)"
    else
        check "Database" "warn" "aios.sqlite not found"
    fi
}

# Function to check disk space
check_disk_space() {
    local available
    available=$(df -h . | tail -1 | awk '{print $4}' | sed 's/G//')
    
    if (( $(echo "$available > 10" | bc -l) )); then
        check "Disk space" "pass" "${available}G available"
    elif (( $(echo "$available > 5" | bc -l) )); then
        check "Disk space" "warn" "${available}G available" "Low disk space"
    else
        check "Disk space" "fail" "${available}G available" "Critical: below 5G"
    fi
}

# Function to print summary
print_summary() {
    if [ "$JSON_OUTPUT" = true ]; then
        echo "{"
        echo "  \"timestamp\": \"$(date -Iseconds)\","
        echo "  \"total_checks\": $TOTAL_CHECKS,"
        echo "  \"passed\": $PASSED_CHECKS,"
        echo "  \"failed\": $FAILED_CHECKS,"
        echo "  \"warnings\": $WARNINGS,"
        echo "  \"status\": \"$([ $FAILED_CHECKS -eq 0 ] && echo "healthy" || echo "unhealthy")\","
        echo "  \"results\": ["
        
        local first=true
        for result in "${RESULTS[@]}"; do
            if [ "$first" = true ]; then
                first=false
            else
                echo ","
            fi
            echo "    $result"
        done
        
        echo "  ]"
        echo "}"
    else
        echo ""
        echo "========================================="
        echo "Health Check Summary"
        echo "========================================="
        echo -e "Total checks:  $TOTAL_CHECKS"
        echo -e "${GREEN}Passed:        $PASSED_CHECKS${NC}"
        echo -e "${RED}Failed:        $FAILED_CHECKS${NC}"
        echo -e "${YELLOW}Warnings:      $WARNINGS${NC}"
        echo ""
        
        if [ $FAILED_CHECKS -eq 0 ]; then
            echo -e "${GREEN}✅ System is HEALTHY${NC}"
        else
            echo -e "${RED}❌ System is UNHEALTHY${NC}"
        fi
        echo "========================================="
    fi
}

# Main execution
main() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo "🏥 AIOS Health Check"
        echo "Timestamp: $(date)"
        echo "API URL: $API_URL"
        echo ""
        echo "Checking services..."
    fi
    
    # Check services
    check_service "API Server" "aios-api-1"
    check_service "Dashboard" "aios-dashboard-1"
    check_service "Autopilot" "aios-autopilot-1"
    check_service "Prometheus" "aios-prometheus-1"
    check_service "Grafana" "aios-grafana-1"
    
    if [ "$JSON_OUTPUT" = false ]; then
        echo ""
        echo "Checking endpoints..."
    fi
    
    # Check HTTP endpoints
    check_api_endpoints
    
    if [ "$JSON_OUTPUT" = false ]; then
        echo ""
        echo "Checking system..."
    fi
    
    # Check system components
    check_database
    check_tests
    check_webhooks
    check_backups
    check_disk_space
    
    # Print summary
    print_summary
    
    # Exit with appropriate code
    if [ $FAILED_CHECKS -gt 0 ]; then
        exit 1
    fi
}

# Run main
main
