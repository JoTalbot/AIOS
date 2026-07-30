"""
AIOS Global Knowledge Graph (NetworkX GraphRAG Simulator)
Глобальная графовая память для глубоких логических связей.
"""
import networkx as nx

class GraphMemory:
    def __init__(self):
        self.G = nx.DiGraph()
        
    def add_insight(self, subject: str, relation: str, obj: str):
        self.G.add_edge(subject, obj, relation=relation)
        print(f"🕸️ [GraphRAG] Создана связь: [{subject}] --({relation})--> [{obj}]")
        
    def query_graph(self, node: str):
        print(f"🔍 [GraphRAG] Поиск знаний вокруг узла: [{node}]")
        if node in self.G:
            neighbors = self.G.edges(node, data=True)
            for s, o, data in neighbors:
                print(f"  -> Известно: {s} {data['relation']} {o}")
            return neighbors
        print("  -> Нет данных в Графе.")
        return []

if __name__ == "__main__":
    gm = GraphMemory()
    gm.add_insight("OpenAI", "provides", "GPT-4")
    gm.add_insight("AIOS", "integrates", "OpenAI")
    gm.query_graph("AIOS")
