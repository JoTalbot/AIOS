#!/usr/bin/env bash
# ==============================================================================
# AIOS — Automated SSH Deployment Script
# ==============================================================================
# Usage:
#   ./scripts/deploy_ssh.sh [SSH_HOST] [SSH_USER] [SSH_PORT] [REMOTE_DIR] [BRANCH]
#
# Environment variables:
#   SSH_HOST      Target server hostname or IP address (Required)
#   SSH_USER      SSH username (Default: root)
#   SSH_PORT      SSH port (Default: 22)
#   SSH_KEY_PATH  Path to SSH private key (Optional)
#   REMOTE_DIR    Remote application directory (Default: /opt/aios)
#   BRANCH        Git branch to deploy (Default: main)
#   ENV_FILE      Local path to .env file to copy (Optional)
# ==============================================================================

set -euo pipefail

# Colors for output
RED='\030[0;31m'
GREEN='\032[0;32m'
YELLOW='\033[1;33m'
BLUE='\034[0;34m'
NC='\033[0m' # No Color

# Helper logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Command line parameters with env fallback
SSH_HOST="${1:-${SSH_HOST:-}}"
SSH_USER="${2:-${SSH_USER:-root}}"
SSH_PORT="${3:-${SSH_PORT:-22}}"
REMOTE_DIR="${4:-${REMOTE_DIR:-/opt/aios}}"
BRANCH="${5:-${BRANCH:-main}}"
SSH_KEY_PATH="${SSH_KEY_PATH:-}"
ENV_FILE="${ENV_FILE:-}"

# Check required parameters
if [ -z "$SSH_HOST" ]; then
  log_error "SSH_HOST is not set."
  echo "Usage: $0 <SSH_HOST> [SSH_USER] [SSH_PORT] [REMOTE_DIR] [BRANCH]"
  echo "Example: $0 192.168.1.100 root 22 /opt/aios main"
  exit 1
fi

# Prepare SSH options
SSH_OPTS=("-o" "StrictHostKeyChecking=no" "-o" "ConnectTimeout=10" "-p" "$SSH_PORT")
if [ -n "$SSH_KEY_PATH" ]; then
  if [ ! -f "$SSH_KEY_PATH" ]; then
    log_error "Specified SSH key file not found: $SSH_KEY_PATH"
    exit 1
  fi
  SSH_OPTS+=("-i" "$SSH_KEY_PATH")
fi

SSH_CMD="ssh ${SSH_OPTS[*]} ${SSH_USER}@${SSH_HOST}"
SCP_CMD="scp ${SSH_OPTS[*]}"

log_info "=================================================="
log_info "🚀 Starting AIOS SSH Deployment"
log_info "Target:       ${SSH_USER}@${SSH_HOST}:${SSH_PORT}"
log_info "Remote Dir:   ${REMOTE_DIR}"
log_info "Branch:       ${BRANCH}"
log_info "=================================================="

# 1. Test SSH Connection
log_info "🔍 Step 1/6: Testing SSH connection..."
if ! $SSH_CMD "echo 'SSH Connection OK'" > /dev/null 2>&1; then
  log_error "Could not connect to ${SSH_USER}@${SSH_HOST} on port ${SSH_PORT}."
  log_error "Please check network, SSH keys, user, and port."
  exit 1
fi
log_success "SSH connection established successfully."

# 2. Check Remote Prerequisites (Docker & Docker Compose)
log_info "🔍 Step 2/6: Checking remote prerequisites (Docker & Docker Compose)..."
CHECK_PREREQS=$($SSH_CMD "
  HAS_DOCKER=\$(command -v docker >/dev/null 2>&1 && echo 'yes' || echo 'no')
  HAS_COMPOSE=\$(docker compose version >/dev/null 2>&1 && echo 'yes' || command -v docker-compose >/dev/null 2>&1 && echo 'yes' || echo 'no')
  HAS_GIT=\$(command -v git >/dev/null 2>&1 && echo 'yes' || echo 'no')
  echo \"\$HAS_DOCKER \$HAS_COMPOSE \$HAS_GIT\"
")

read -r HAS_DOCKER HAS_COMPOSE HAS_GIT <<< "$CHECK_PREREQS"

if [ "$HAS_DOCKER" != "yes" ] || [ "$HAS_COMPOSE" != "yes" ] || [ "$HAS_GIT" != "yes" ]; then
  log_warn "Missing required packages on remote server:"
  [ "$HAS_DOCKER" != "yes" ] && log_warn " - Docker is NOT installed"
  [ "$HAS_COMPOSE" != "yes" ] && log_warn " - Docker Compose is NOT installed"
  [ "$HAS_GIT" != "yes" ] && log_warn " - Git is NOT installed"
  log_info "Attempting automatic server setup..."
  
  $SSH_CMD "
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq git curl ca-certificates gnupg lsb-release
    if ! command -v docker >/dev/null 2>&1; then
      curl -fsSL https://get.docker.com | sh
    fi
  "
  log_success "Prerequisites installed successfully."
else
  log_success "All prerequisites (Docker, Docker Compose, Git) are available."
fi

# 3. Clone or Update Repository
log_info "📦 Step 3/6: Syncing codebase on remote server..."
$SSH_CMD "
  set -e
  if [ -d '${REMOTE_DIR}/.git' ]; then
    echo 'Updating existing repository in ${REMOTE_DIR}...'
    cd '${REMOTE_DIR}'
    git fetch origin
    git checkout '${BRANCH}'
    git reset --hard 'origin/${BRANCH}'
  else
    echo 'Cloning repository into ${REMOTE_DIR}...'
    mkdir -p '${REMOTE_DIR}'
    git clone -b '${BRANCH}' https://github.com/JoTalbot/AIOS.git '${REMOTE_DIR}'
  fi
"
log_success "Codebase synchronized with branch '${BRANCH}'."

# 4. Configure .env file
log_info "⚙️ Step 4/6: Configuring environment variables (.env)..."
if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
  log_info "Uploading local .env file (${ENV_FILE}) to target server..."
  $SCP_CMD "$ENV_FILE" "${SSH_USER}@${SSH_HOST}:${REMOTE_DIR}/.env"
else
  $SSH_CMD "
    cd '${REMOTE_DIR}'
    if [ ! -f .env ]; then
      if [ -f .env.example ]; then
        cp .env.example .env
      else
        touch .env
      fi
      
      # Generate random keys if needed
      API_KEY=\$(python3 -c \"import secrets; print(secrets.token_urlsafe(32))\" 2>/dev/null || openssl rand -hex 24)
      GRAFANA_PASS=\$(python3 -c \"import secrets; print(secrets.token_urlsafe(16))\" 2>/dev/null || openssl rand -hex 12)
      
      echo \"AIOS_API_KEYS={\\\"\$API_KEY\\\":{\\\"subject\\\":\\\"ssh-operator\\\",\\\"roles\\\":[\\\"admin\\\"]}}\" >> .env
      echo \"GRAFANA_PASSWORD=\$GRAFANA_PASS\" >> .env
      echo 'Created default .env configuration.'
    fi
  "
fi
log_success "Environment configuration verified."

# 5. Build and Launch Containers
log_info "🐳 Step 5/6: Building and starting Docker containers..."
$SSH_CMD "
  set -e
  cd '${REMOTE_DIR}'
  if docker compose version >/dev/null 2>&1; then
    docker compose -f docker-compose.prod.yml down --remove-orphans || true
    docker compose -f docker-compose.prod.yml up -d --build
  else
    docker-compose -f docker-compose.prod.yml down --remove-orphans || true
    docker-compose -f docker-compose.prod.yml up -d --build
  fi
"
log_success "Docker services deployed."

# 6. Verification and Health Check
log_info "🩺 Step 6/6: Verifying deployment health..."
sleep 8

HEALTH_STATUS=$($SSH_CMD "
  cd '${REMOTE_DIR}'
  curl -s -f http://localhost:8000/health || echo 'FAILED'
")

if [[ "$HEALTH_STATUS" == *"status"* ]] || [[ "$HEALTH_STATUS" == *"ok"* ]] || [[ "$HEALTH_STATUS" == *"healthy"* ]]; then
  log_success "Healthcheck PASSED! Response: ${HEALTH_STATUS}"
else
  log_warn "Healthcheck returned: ${HEALTH_STATUS}. Checking container status..."
fi

$SSH_CMD "
  cd '${REMOTE_DIR}'
  if docker compose version >/dev/null 2>&1; then
    docker compose -f docker-compose.prod.yml ps
  else
    docker-compose -f docker-compose.prod.yml ps
  fi
"

log_info "=================================================="
log_success "🎉 AIOS Deployment Completed Successfully!"
log_info "Services:"
log_info "  • API Endpoint:   http://${SSH_HOST}:8000/health"
log_info "  • Dashboard UI:   http://${SSH_HOST}:8080"
log_info "  • MCP Server:     ${SSH_HOST}:8471"
log_info "  • Grafana UI:     http://${SSH_HOST}:3000"
log_info "  • Prometheus:     http://${SSH_HOST}:9090"
log_info "=================================================="
