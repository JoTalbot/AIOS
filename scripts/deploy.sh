#!/bin/bash
# AIOS Production Deployment Script
# Usage: ./scripts/deploy.sh [dev|staging|production]

set -e

ENVIRONMENT=${1:-dev}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="deploy_${ENVIRONMENT}_${TIMESTAMP}.log"

echo "🚀 AIOS Deployment Script"
echo "Environment: $ENVIRONMENT"
echo "Timestamp: $TIMESTAMP"
echo "Log file: $LOG_FILE"
echo ""

# Function to log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check prerequisites
check_prerequisites() {
    log "🔍 Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log "❌ Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log "❌ Docker Compose is not installed"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log "❌ Python 3 is not installed"
        exit 1
    fi
    
    log "✅ Prerequisites check passed"
}

# Function to run tests
run_tests() {
    log "🧪 Running tests..."
    
    python3 -m pytest -q --tb=short 2>&1 | tee -a "$LOG_FILE"
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        log "❌ Tests failed! Aborting deployment."
        exit 1
    fi
    
    log "✅ All tests passed"
}

# Function to backup database
backup_database() {
    log "💾 Creating database backup..."
    
    if [ -f "aios.sqlite" ]; then
        BACKUP_FILE="backups/aios_backup_${TIMESTAMP}.sqlite"
        mkdir -p backups
        cp aios.sqlite "$BACKUP_FILE"
        log "✅ Database backed up to $BACKUP_FILE"
    else
        log "ℹ️  No existing database found, skipping backup"
    fi
}

# Function to deploy
deploy() {
    log "🐳 Starting deployment..."
    
    case $ENVIRONMENT in
        dev)
            log "Deploying to development..."
            docker-compose up -d --build
            ;;
        staging)
            log "Deploying to staging..."
            docker-compose -f docker-compose.prod.yml up -d --build
            ;;
        production)
            log "Deploying to production..."
            
            # Confirm production deployment
            read -p "⚠️  Are you sure you want to deploy to PRODUCTION? (yes/no): " confirm
            if [ "$confirm" != "yes" ]; then
                log "❌ Deployment cancelled"
                exit 1
            fi
            
            docker-compose -f docker-compose.prod.yml up -d --build
            ;;
        *)
            log "❌ Unknown environment: $ENVIRONMENT"
            log "Usage: $0 [dev|staging|production]"
            exit 1
            ;;
    esac
    
    log "✅ Deployment started"
}

# Function to verify deployment
verify_deployment() {
    log "🔍 Verifying deployment..."
    
    # Wait for services to start
    sleep 10
    
    # Check health endpoint
    HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")
    
    if [ "$HEALTH_CHECK" != "200" ]; then
        log "❌ Health check failed (HTTP $HEALTH_CHECK)"
        exit 1
    fi
    
    log "✅ Health check passed"
    
    # Check metrics endpoint
    METRICS_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/metrics || echo "000")
    
    if [ "$METRICS_CHECK" != "200" ]; then
        log "⚠️  Metrics endpoint not available (HTTP $METRICS_CHECK)"
    else
        log "✅ Metrics endpoint available"
    fi
    
    # Check dashboard
    DASHBOARD_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 || echo "000")
    
    if [ "$DASHBOARD_CHECK" != "200" ]; then
        log "⚠️  Dashboard not available (HTTP $DASHBOARD_CHECK)"
    else
        log "✅ Dashboard available at http://localhost:8080"
    fi
}

# Function to setup webhooks
setup_webhooks() {
    log "🔔 Setting up webhooks..."
    
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        python3 aios_cli.py admin webhooks register \
            --name slack-alerts \
            --url "$SLACK_WEBHOOK_URL" \
            --events ban_detected low_success_rate device_offline backup_completed \
            2>&1 | tee -a "$LOG_FILE"
        log "✅ Slack webhook configured"
    else
        log "ℹ️  SLACK_WEBHOOK_URL not set, skipping webhook setup"
    fi
}

# Function to create initial backup
create_initial_backup() {
    log "💾 Creating initial backup..."
    
    python3 aios_cli.py admin backup create \
        --label "post-deploy-${ENVIRONMENT}" \
        --mode full \
        2>&1 | tee -a "$LOG_FILE"
    
    log "✅ Initial backup created"
}

# Function to show status
show_status() {
    log "📊 Deployment status:"
    echo ""
    echo "Services:"
    docker-compose ps 2>/dev/null || docker-compose -f docker-compose.prod.yml ps
    echo ""
    echo "Health:"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "Health endpoint not available"
    echo ""
    echo "Webhook health:"
    python3 aios_cli.py admin webhooks health 2>/dev/null || echo "Webhook health not available"
    echo ""
}

# Main execution
main() {
    log "========================================="
    log "AIOS Deployment Started"
    log "========================================="
    
    check_prerequisites
    run_tests
    backup_database
    deploy
    verify_deployment
    setup_webhooks
    create_initial_backup
    show_status
    
    log "========================================="
    log "✅ Deployment completed successfully!"
    log "========================================="
    log ""
    log "Next steps:"
    log "  1. Check logs: docker-compose logs -f"
    log "  2. Monitor metrics: curl http://localhost:8000/metrics"
    log "  3. Open dashboard: http://localhost:8080"
    log "  4. Open Grafana: http://localhost:3000 (admin/admin)"
    log ""
    log "Log file: $LOG_FILE"
}

# Run main
main
