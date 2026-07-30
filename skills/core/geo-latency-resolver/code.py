import json

def map_geo_latency():
    # Simulation of geo-routing logic
    geo_map = {
        'US-East': 35.0, # Known from AWS node
        'EU-Central': 2.0, # Known from Parent
        'Home-UA': 5.0    # Known from Ubu
    }
    print(f'[GEO] Global latency map: {geo_map}')
    return geo_map

if __name__ == '__main__':
    map_geo_latency()
