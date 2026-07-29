
import hashlib
from collections import defaultdict


class IntentDiscovery:
    def __init__(self):
        self.min_cluster = 5
    
    def analyze(self, messages: list[dict]) -> dict:
        uncertain = [m for m in messages if m.get("confidence", 1.0) < 0.6]
        if not uncertain: return {"status": "no_uncertain"}
        
        clusters = defaultdict(list)
        for msg in uncertain:
            words = sorted(set(msg.get("text", "").lower().split()))
            key = hashlib.md5(" ".join(words).encode()).hexdigest()[:8]
            clusters[key].append(msg)
        
        new_intents = []
        for key, msgs in clusters.items():
            if len(msgs) >= self.min_cluster:
                words = [w for m in msgs for w in m.get("text", "").lower().split() if len(w) > 3]
                top = sorted(set(words), key=words.count, reverse=True)[:3]
                new_intents.append({"cluster": key, "count": len(msgs), "suggested_name": "_".join(top)})
        
        return {"status": "analyzed", "new_intents": new_intents}

intent_discovery = IntentDiscovery()
