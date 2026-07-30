#!/bin/bash
# Sync data from /opt/aios to /root/AIOS/data
# Run via cron every 30 minutes

SYNC_SRC="/opt/aios"
SYNC_DST="/root/AIOS/data"

# Sync OLX database
if [ -f "$SYNC_SRC/data/olx_http.sqlite" ]; then
    cp -u "$SYNC_SRC/data/olx_http.sqlite" "$SYNC_DST/olx_http.sqlite"
    echo "[$(date)] Synced olx_http.sqlite"
fi

# Sync AIOS database
if [ -f "$SYNC_SRC/aios.sqlite" ]; then
    cp -u "$SYNC_SRC/aios.sqlite" "$SYNC_DST/aios.sqlite"
    echo "[$(date)] Synced aios.sqlite"
fi

# Sync subscriptions database
if [ -f "$SYNC_SRC/data/olx_subs.sqlite" ]; then
    cp -u "$SYNC_SRC/data/olx_subs.sqlite" "$SYNC_DST/olx_subs.sqlite"
    echo "[$(date)] Synced olx_subs.sqlite"
fi
