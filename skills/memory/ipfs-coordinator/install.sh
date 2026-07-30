#!/usr/bin/env bash
# Octopus IPFS Install + Auto-Init Script (Instruction #54)
set -euo pipefail
IPFS_VERSION="v0.26.0"
ARCH="linux-amd64"
URL="https://dist.ipfs.tech/kubo/${IPFS_VERSION}/kubo_${IPFS_VERSION}_${ARCH}.tar.gz"

echo "[1/4] Downloading kubo ${IPFS_VERSION}..."
curl -sSL "$URL" -o /tmp/kubo.tar.gz

echo "[2/4] Extracting..."
tar -xzf /tmp/kubo.tar.gz -C /tmp
mv /tmp/kubo/ipfs /usr/local/bin/ipfs
rm -rf /tmp/kubo /tmp/kubo.tar.gz

echo "[3/4] Initializing IPFS..."
ipfs init --profile server,flatfs 2>/dev/null || true

echo "[4/4] Configuring..."
ipfs config Addresses.API /ip4/127.0.0.1/tcp/5001 2>/dev/null || true
ipfs config Addresses.Gateway /ip4/127.0.0.1/tcp/8080 2>/dev/null || true

echo "IPFS installed and initialized. Start with: ipfs daemon"
