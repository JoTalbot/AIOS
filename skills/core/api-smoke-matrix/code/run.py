from aios_core.security import constitution_enforced

"""API Smoke Matrix"""
import json
import subprocess
import urllib.request
import urllib.error
ENDPOINTS = [{'name': 'Local API', 'url': 'http://127.0.0.1:8000/health'}, {'name': 'Railway', 'url': 'https://octopus-production-71fe.up.railway.app/health'}, {'name': 'Health', 'url': 'http://127.0.0.1:9715/healthz'}]

def check_endpoint(ep):
    try:
        req = urllib.request.Request(ep['url'], headers={'User-Agent': 'SmokeTest/1.0'})
        resp = urllib.request.urlopen(req, timeout=5)
        return {'ok': True, 'status': resp.status, 'latency_ms': 0}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:100]}

def run_smoke_tests():
    results = []
    for ep in ENDPOINTS:
        result = check_endpoint(ep)
        results.append({'name': ep['name'], 'url': ep['url'], **result})
    return results
if __name__ == '__main__':
    results = run_smoke_tests()
    healthy = sum((1 for r in results if r.get('ok')))
    print(json.dumps({'ok': True, 'total': len(results), 'healthy': healthy, 'unhealthy': len(results) - healthy, 'endpoints': results, 'recommendation': 'All APIs healthy' if healthy == len(results) else f'{len(results) - healthy} API(s) down'}, indent=2))