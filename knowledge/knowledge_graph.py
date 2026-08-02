class KnowledgeGraph:
    """AIOS knowledge graph foundation."""

    def add(self, entity, relation):
        return {
            "entity": entity,
            "relation": relation,
            "stored": True
        }
