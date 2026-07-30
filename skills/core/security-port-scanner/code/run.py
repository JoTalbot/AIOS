#!/usr/bin/env python3
"""Security Port Scanner - Local open ports check"""
import json
import subprocess

def get_listening_ports():
    """Get listening TCP/UDP ports"""
    result = subprocess.run(
        ["ss", "-tuln"], capture_output=True, text=True
    )
    
    ports = []
    for line in result.stdout.split("\n")[1:]:
        if line.strip():
            parts = line.split()
            if len(parts) >= 5:
                proto = parts[0].lower()
                local_addr = parts[4]
                if ":" in local_addr:
                    addr, port = local_addr.rsplit(":", 1)
                    ports.append({"proto": proto, "address": addr, "port": port})
    
    return ports

def analyze_ports(ports):
    """Analyze ports for security"""
    suspicious = []
    common_services = {"22": "SSH", "80": "HTTP", "443": "HTTPS", "8000": "API", "8080": "Alt-HTTP"}
    
    for p in ports:
        port = p.get("port", "")
        if port in common_services:
            p["service"] = common_services[port]
        
        # Check for high ports exposed
        try:
            if int(port) > 9000 and p.get("address") not in ["127.0.0.1", "::1"]:
                suspicious.append(f"High port {port} on {p.get('address')}")
        except:
            pass
    
    return suspicious

def main():
    ports = get_listening_ports()
    suspicious = analyze_ports(ports)
    
    print(json.dumps({
        "ok": len(suspicious) == 0,
        "total_ports": len(ports),
        "suspicious": suspicious,
        "ports": ports[:20]  # Top 20
    }, indent=2))

if __name__ == "__main__":
    main()
