#!/usr/bin/env python3
"""SSL Certificate Expiry Checker - Real cert check"""
import json
import ssl
import socket
from datetime import datetime, timezone
from urllib.request import urlopen

TARGETS = [
    ("octopus-production-71fe.up.railway.app", 443),
    ("traff.tplinkdns.com", 443),
]

def check_cert(domain, port=443):
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                expiry = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                expiry_utc = expiry.replace(tzinfo=timezone.utc)
                days_left = (expiry_utc - datetime.now(timezone.utc)).days
        
        return {
            "domain": domain,
            "ok": True,
            "expires": expiry_utc.isoformat(),
            "days_left": days_left,
            "status": "CRITICAL" if days_left < 7 else "WARNING" if days_left < 30 else "OK"
        }
    except Exception as e:
        return {"domain": domain, "ok": False, "error": str(e)}

def main():
    results = [check_cert(domain, port) for domain, port in TARGETS]
    healthy = sum(1 for r in results if r.get("ok") and r.get("days_left", 999) > 30)
    
    print(json.dumps({
        "ok": healthy == len(TARGETS),
        "certs_checked": len(TARGETS),
        "healthy": healthy,
        "certificates": results
    }, indent=2))

if __name__ == "__main__":
    main()
