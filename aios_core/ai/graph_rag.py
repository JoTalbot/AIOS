import networkx as nx
from typing import Dict, Any

class GraphRAG:
    def __init__(self):
        self.graph = nx.DiGraph()
    
    def add_entity(self, entity_id: str, entity_type: str, properties: Dict[str, Any]):
        self.graph.add_node(entity_id, type=entity_type, **properties)
    
    def add_relationship(self, source: str, target: str, relation: str, weight: float = 1.0):
        self.graph.add_edge(source, target, relation=relation, weight=weight)
    
    def query_context(self, query_entity: str, max_depth: int = 2) -> str:
        if query_entity not in self.graph:
            return "Entity not found."
        subgraph = nx.ego_graph(self.graph, query_entity, radius=max_depth)
        context = f"Graph Context for {query_entity}:\n"
        for node, data in subgraph.nodes(data=True):
            context += f"- {node} ({data.get("type", "entity")})\n"
        return context

graph_rag = GraphRAG()
