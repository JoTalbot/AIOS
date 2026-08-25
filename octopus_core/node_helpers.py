import json
import os

REPUTATION_DB = '/var/lib/octopus/reputation.json'

def get_node_power(node_id):
    """Compute the power weight of a node from the reputation database.

    Args:
        node_id: Node identifier key in ``REPUTATION_DB``.

    Returns:
        ``1.0 + score/100`` rounded to two decimals; falls back to ``1.0``
        when the database is missing or unreadable.
    """
    if not os.path.exists(REPUTATION_DB): return 1.0
    try:
        with open(REPUTATION_DB, 'r') as f:
            data = json.load(f)
        score = data.get(node_id, {}).get('score', 0)
        return round(1.0 + (score / 100.0), 2)
    except:
        return 1.0
