#!/usr/bin/env bash
# ==============================================================================
# AIOS — Target Remote Server Initial Provisioning Script
# ==============================================================================
# Runs on or against a clean Linux server (Ubuntu 22.04 / 24.04 recommended)
# Installs:
#   - Docker Engine & Docker Compose v2
#   - Git, Python3, pip, curl, jq, htop, build-essential
#   - KVM / QEMU (optional support for Android Emulators)
#   - Systemd background service for AIOS Stack
# ==============================================================================

set -euo pipefail

# Color indicators
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== AIOS Remote Server Initial Provisioning ===${NC}"

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: This script must be run as root (or via sudo).${NC}"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo -e "${BLUE}[1/5] Updating system packages...${NC}"
apt-get update -qq
apt-get upgrade -y -qq

echo -e "${BLUE}[2/5] Installing base utilities...${NC}"
apt-get install -y -qq \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    python3 \
    python3-pip \
    python3-venv \
    jq \
    htop \
    ufw \
    net-tools \
    build-essential \
    libssl-dev

echo -e "${BLUE}[3/5] Installing Docker & Docker Compose...${NC}"
if ! command -v docker >/dev/null 2>&1; then
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}Docker installed successfully.${NC}"
else
    echo -e "${GREEN}Docker is already installed.${NC}"
fi

echo -e "${BLUE}[4/5] Checking hardware virtualization (KVM) for Android Emulators...${NC}"
if grep -E -q 'vmx|svm' /proc/cpuinfo; then
    echo -e "${GREEN}KVM acceleration supported. Installing QEMU/KVM tools...${NC}"
    apt-get install -y -qq cpu-checker qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils || true
else
    echo -e "${YELLOW}Notice: CPU hardware virtualization not detected. Software emulation will be used if Android container is launched.${NC}"
fi

echo -e "${BLUE}[5/5] Configuring firewall (UFW)...${NC}"
if command -v ufw >/dev/null 2>&1; then
    ufw allow 22/tcp || true
    ufw allow 8000/tcp || true # AIOS API
    ufw allow 8080/tcp || true # AIOS Dashboard
    ufw allow 8471/tcp || true # AIOS MCP
    ufw allow 3000/tcp || true # Grafana
    ufw allow 9090/tcp || true # Prometheus
    echo "y" | ufw enable || true
    echo -e "${GREEN}Firewall configured for AIOS ports (22, 8000, 8080, 8471, 3000, 9090).${NC}"
fi

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}🎉 Server Provisioning Complete!${NC}"
echo -e "${GREEN}Docker:          $(docker --version)${NC}"
echo -e "${GREEN}Docker Compose:  $(docker compose version)${NC}"
echo -e "${GREEN}Ready for AIOS deployment via scripts/deploy_ssh.sh${NC}"
echo -e "${GREEN}==================================================${NC}"
